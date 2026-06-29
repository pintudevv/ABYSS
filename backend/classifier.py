"""
StealthOS — ML & Heuristic Classifier (Step 4)
==============================================
Loads static features (results/features.json) and sandbox behavior (results/behavior.json).
Classifies threat using XGBoost/Random Forest/Autoencoder, falling back to heuristic evaluation.
Outputs classification_result.json in results/ directory.
"""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional ML library imports
# ---------------------------------------------------------------------------
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("classifier")

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"

# ---------------------------------------------------------------------------
# Threat Categories and API maps
# ---------------------------------------------------------------------------
THREAT_TYPES = ["Clean", "Trojan", "Ransomware", "Spyware", "Adware"]

RANSOMWARE_APIS = {"CryptEncrypt", "CryptGenKey", "DeleteFileA", "MoveFileExA"}
TROJAN_APIS = {"VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread", "OpenProcess", "NtUnmapViewOfSection"}
SPYWARE_APIS = {"GetClipboardData", "SetWindowsHookEx", "GetAsyncKeyState"}
NETWORK_APIS = {"connect", "send", "WSASend", "InternetOpenA", "HttpSendRequestA"}

# ---------------------------------------------------------------------------
# Classifier Class
# ---------------------------------------------------------------------------
class StealthClassifier:
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.xgb_model = None
        self.rf_model = None
        self.autoencoder = None
        self.is_ml_loaded = False
        self._load_models()

    def _load_models(self):
        xgb_path = self.models_dir / "xgboost_model.pkl"
        rf_path = self.models_dir / "rf_model.pkl"
        ae_path = self.models_dir / "autoencoder.pt"

        try:
            if xgb_path.exists():
                with open(xgb_path, "rb") as f:
                    self.xgb_model = pickle.load(f)
                log.info("XGBoost model loaded successfully")
            if rf_path.exists():
                with open(rf_path, "rb") as f:
                    self.rf_model = pickle.load(f)
                log.info("Random Forest model loaded successfully")
            if ae_path.exists() and HAS_TORCH:
                # Define Autoencoder class structure so PyTorch can unpickle it
                class Autoencoder(nn.Module):
                    def __init__(self):
                        super().__init__()
                        self.encoder = nn.Sequential(
                            nn.Linear(2381, 256),
                            nn.ReLU(),
                            nn.Linear(256, 64),
                            nn.ReLU()
                        )
                        self.decoder = nn.Sequential(
                            nn.Linear(64, 256),
                            nn.ReLU(),
                            nn.Linear(256, 2381)
                        )
                    def forward(self, x):
                        return self.decoder(self.encoder(x))
                
                # Import Autoencoder into global namespace so unpickler resolves it
                import sys
                sys.modules['__main__'].Autoencoder = Autoencoder
                
                self.autoencoder = torch.load(str(ae_path), weights_only=False)
                log.info("PyTorch Autoencoder model loaded successfully")
            
            if self.xgb_model or self.rf_model or self.autoencoder:
                self.is_ml_loaded = True
        except Exception as e:
            log.warning(f"Failed to load ML models: {e}. Defaulting to Heuristic Engine.")

    def run_classification(self, static_data: dict, behavior_data: dict) -> dict:
        """Runs the combined classification pipeline using real ML models and SHAP explainer."""
        filepath = static_data.get("file_info", {}).get("filepath")
        
        if self.is_ml_loaded and filepath and Path(filepath).exists():
            log.info(f"ML models active. Performing inference on {filepath}...")
            try:
                # 1. Stub NumPy deprecated aliases for SHAP compatibility
                import numpy as np
                if not hasattr(np, "int"):
                    np.int = int
                if not hasattr(np, "bool"):
                    np.bool = bool
                if not hasattr(np, "float"):
                    np.float = float

                import sklearn.feature_extraction
                original_transform = sklearn.feature_extraction.FeatureHasher.transform
                def patched_transform(self, raw_X):
                    if self.input_type == "string":
                        new_X = []
                        for x in raw_X:
                            if isinstance(x, str):
                                new_X.append([x])
                            else:
                                new_X.append(x)
                        raw_X = new_X
                    return original_transform(self, raw_X)
                sklearn.feature_extraction.FeatureHasher.transform = patched_transform

                # 2. Stub LIEF error classes to maintain compatibility with newer LIEF versions
                import lief
                for attr in ["bad_format", "bad_file", "pe_error", "parser_error", "read_out_of_bound", "corrupted"]:
                    if not hasattr(lief, attr):
                        setattr(lief, attr, Exception)

                import ember
                extractor = ember.PEFeatureExtractor(2)
                with open(filepath, "rb") as f:
                    file_data = f.read()
                
                features_vec = extractor.feature_vector(file_data)
                features_vec = np.array(features_vec, dtype=np.float32).reshape(1, -1)

                # 3. Perform model predictions
                rf_pred = int(self.rf_model.predict(features_vec)[0])
                rf_prob = self.rf_model.predict_proba(features_vec)[0]
                
                xgb_pred = int(self.xgb_model.predict(features_vec)[0])
                xgb_prob = self.xgb_model.predict_proba(features_vec)[0]

                # 4. Perform PyTorch Autoencoder reconstruction
                ae_tensor = torch.tensor(features_vec, dtype=torch.float32)
                self.autoencoder.eval()
                with torch.no_grad():
                    ae_reconstructed = self.autoencoder(ae_tensor)
                    ae_loss = float(torch.mean((ae_tensor - ae_reconstructed)**2).item())

                # Zero-Day anomaly detection: threshold derived from real EMBER training (377779820953.6)
                is_zero_day = ae_loss > 377779820953.6
                
                # 5. Compute real SHAP explanation values using TreeExplainer
                import shap
                explainer = shap.TreeExplainer(self.xgb_model)
                raw_shap = explainer.shap_values(features_vec)
                # For binary classifications, TreeExplainer returns shape (1, 2381) or (1, 2381, 2)
                if isinstance(raw_shap, list):
                    # Newer shap returns list for multi-class/binary outputs
                    shap_vec = raw_shap[1][0] if len(raw_shap) > 1 else raw_shap[0][0]
                elif len(raw_shap.shape) == 3:
                    shap_vec = raw_shap[0, :, 1]
                else:
                    shap_vec = raw_shap[0]

                # Map feature indices to names
                shap_explanation = []
                for idx, val in enumerate(shap_vec):
                    if abs(val) > 1e-5:
                        shap_explanation.append({
                            "feature": self._get_ember_feature_name(idx),
                            "value": float(features_vec[0, idx]),
                            "impact": float(val)
                        })

                # Sort by absolute impact
                shap_explanation = sorted(shap_explanation, key=lambda x: abs(x["impact"]), reverse=True)[:10]

                # 6. Blending with Heuristics & Behavior
                decision_path = [
                    f"XGBoost Classifier predicts class {xgb_pred} (malicious probability: {xgb_prob[1]*100:.1f}%)",
                    f"Random Forest Classifier predicts class {rf_pred} (malicious probability: {rf_prob[1]*100:.1f}%)",
                    f"Autoencoder Reconstruction Loss: {ae_loss:.1f} (Zero-Day: {is_zero_day})"
                ]

                # Combine ML scores with behavior (Frida api hooks, registry persistences, network blocks)
                behavior_result = self._evaluate_heuristics(static_data, behavior_data)
                
                # final score is a blend of XGB/RF predictions and dynamic indicators
                ml_score = max(xgb_prob[1], rf_prob[1]) * 100
                
                # If both ML models say benign, we clamp score unless dynamic behavior is highly confident (> 60)
                if xgb_pred == 0 and rf_pred == 0:
                    if behavior_result["confidence"] < 60:
                        total_score = int(min(ml_score, 15))
                        threat_type = "Clean"
                        decision_path.append("ML models predict benign; low-severity heuristics ignored.")
                    else:
                        total_score = int(min(ml_score + behavior_result["confidence"] * 0.5, 100))
                        threat_type = behavior_result["threat_type"]
                else:
                    total_score = int(min(ml_score + min(behavior_result["confidence"] / 2.0, 30), 100))
                    threat_type = behavior_result["threat_type"]
                    if threat_type == "Clean":
                        threat_type = "Trojan" # default fallback for malicious ML

                risk_level = "CLEAN"
                if total_score >= 85:
                    risk_level = "CRITICAL"
                elif total_score >= 60:
                    risk_level = "HIGH"
                elif total_score >= 35:
                    risk_level = "MEDIUM"
                elif total_score >= 15:
                    risk_level = "LOW"

                decision_path.extend(behavior_result["decision_path"])

                return {
                    "threat_type": threat_type,
                    "confidence": total_score,
                    "is_zero_day": is_zero_day,
                    "risk_level": risk_level,
                    "shap_explanation": shap_explanation,
                    "classifier_used": "xgboost_rf_autoencoder",
                    "decision_path": decision_path
                }
            except Exception as e:
                log.warning(f"ML inference/SHAP calculation failed: {e}. Falling back to Heuristics.")
                return self._evaluate_heuristics(static_data, behavior_data)
        else:
            log.info("ML models inactive or file missing. Performing Heuristic analysis...")
            return self._evaluate_heuristics(static_data, behavior_data)

    def _get_ember_feature_name(self, idx: int) -> str:
        if idx < 256:
            return f"byte_histogram_{idx}"
        elif idx < 512:
            return f"byte_entropy_{idx - 256}"
        elif idx < 616:
            return f"string_info_{idx - 512}"
        elif idx < 626:
            general_names = [
                "file_size", "has_debug", "exports_count", "imports_count", 
                "has_relocations", "has_resources", "has_signature", 
                "has_tls", "symbols_count", "subsystem"
            ]
            return f"general_{general_names[idx - 616]}"
        elif idx < 688:
            return f"header_info_{idx - 626}"
        elif idx < 943:
            return f"section_info_{idx - 688}"
        elif idx < 2223:
            return f"import_api_hash_{idx - 943}"
        elif idx < 2351:
            return f"export_api_hash_{idx - 2223}"
        else:
            return f"data_directory_{idx - 2351}"

    def _evaluate_heuristics(self, static: dict, behavior: dict) -> dict:
        decision_path = []
        shap_explanation = []

        # Parse static
        pe = static.get("pe_analysis", {})
        strings = static.get("string_analysis", {})
        
        overall_entropy = pe.get("overall_entropy", 0.0)
        suspicious_import_count = pe.get("suspicious_import_count", 0)
        suspicious_hits = strings.get("suspicious_hits", [])
        urls = strings.get("urls_found", [])

        # Parse behavior
        api_calls = behavior.get("api_calls", [])
        registry_ops = behavior.get("registry_operations", [])
        file_ops = behavior.get("file_operations", [])
        net_connections = behavior.get("network_connections", [])
        signatures = behavior.get("signatures", [])

        static_score = 0
        behavior_score = 0

        # Heuristics: Static
        if pe.get("is_packed"):
            static_score += 25
            decision_path.append("File exhibits packers/obfuscation characteristics (+25)")
            shap_explanation.append({"feature": "pe_packed", "value": 1.0, "impact": 25.0})
        
        if overall_entropy > 7.0:
            static_score += 20
            decision_path.append(f"Highly elevated section entropy: {overall_entropy} (+20)")
            shap_explanation.append({"feature": "pe_entropy", "value": overall_entropy, "impact": 20.0})
        elif overall_entropy > 6.0:
            static_score += 10
            decision_path.append(f"Moderate section entropy: {overall_entropy} (+10)")
            shap_explanation.append({"feature": "pe_entropy", "value": overall_entropy, "impact": 10.0})

        if suspicious_import_count > 0:
            weight = min(suspicious_import_count * 4, 30)
            static_score += weight
            decision_path.append(f"Dangerous PE API imports: {suspicious_import_count} (+{weight})")
            shap_explanation.append({"feature": "suspicious_imports", "value": float(suspicious_import_count), "impact": float(weight)})

        if len(suspicious_hits) > 0:
            weight = min(len(suspicious_hits) * 3, 20)
            static_score += weight
            decision_path.append(f"Suspicious string matches: {len(suspicious_hits)} (+{weight})")
            shap_explanation.append({"feature": "suspicious_strings", "value": float(len(suspicious_hits)), "impact": float(weight)})

        # Heuristics: Behavior
        api_names = {call.get("api", "") for call in api_calls}
        
        # Ransomware checks
        ransomware_score = 0
        ransom_apis = api_names.intersection(RANSOMWARE_APIS)
        if ransom_apis:
            ransomware_score += len(ransom_apis) * 15
            decision_path.append(f"Ransomware API hooks triggered: {list(ransom_apis)} (+{len(ransom_apis) * 15})")
            shap_explanation.append({"feature": "ransomware_apis", "value": float(len(ransom_apis)), "impact": len(ransom_apis) * 15.0})
        
        # Trojan checks
        trojan_score = 0
        trojan_apis = api_names.intersection(TROJAN_APIS)
        if trojan_apis:
            trojan_score += len(trojan_apis) * 20
            decision_path.append(f"Trojan injection API hooks triggered: {list(trojan_apis)} (+{len(trojan_apis) * 20})")
            shap_explanation.append({"feature": "trojan_injection_apis", "value": float(len(trojan_apis)), "impact": len(trojan_apis) * 20.0})

        # Spyware checks
        spyware_score = 0
        spyware_apis = api_names.intersection(SPYWARE_APIS)
        if spyware_apis:
            spyware_score += len(spyware_apis) * 15
            decision_path.append(f"Spyware/credential stealing hooks triggered: {list(spyware_apis)} (+{len(spyware_apis) * 15})")
            shap_explanation.append({"feature": "spyware_apis", "value": float(len(spyware_apis)), "impact": len(spyware_apis) * 15.0})

        # Network traffic
        if net_connections:
            weight = min(len(net_connections) * 5, 20)
            behavior_score += weight
            decision_path.append(f"C2/outbound connections made: {len(net_connections)} (+{weight})")
            shap_explanation.append({"feature": "network_connections", "value": float(len(net_connections)), "impact": float(weight)})

        # Registry tampering (Persistence)
        susp_reg = [r for r in registry_ops if any(k in r.get("key", "") for k in ("Run", "Services", "Winlogon"))]
        if susp_reg:
            behavior_score += 15
            decision_path.append(f"Registry persistence hooks hit (+15)")
            shap_explanation.append({"feature": "persistence_registry", "value": float(len(susp_reg)), "impact": 15.0})

        # Compile final scores
        behavior_score += max(ransomware_score, trojan_score, spyware_score)
        total_score = min(static_score + behavior_score, 100)

        # Classification mapping
        threat_type = "Clean"
        if total_score >= 40:
            scores = {
                "Ransomware": ransomware_score + (15 if any("ransom" in s.get("pattern", "") for s in suspicious_hits) else 0),
                "Trojan": trojan_score + (15 if pe.get("is_packed") else 0),
                "Spyware": spyware_score + (15 if any("keylog" in s.get("pattern", "") for s in suspicious_hits) else 0),
                "Adware": len(urls) * 2,
            }
            max_threat = max(scores, key=scores.get)
            if scores[max_threat] > 5:
                threat_type = max_threat
            else:
                threat_type = "Trojan"

        risk_level = "CLEAN"
        if total_score >= 85:
            risk_level = "CRITICAL"
        elif total_score >= 60:
            risk_level = "HIGH"
        elif total_score >= 35:
            risk_level = "MEDIUM"
        elif total_score >= 15:
            risk_level = "LOW"

        # Check for zero-day signature
        is_zero_day = False
        if total_score >= 50 and not pe.get("has_debug_info") and pe.get("is_packed"):
            is_zero_day = True
            decision_path.append("Zero-day signature: packed executable with no debug information structures")

        if not shap_explanation:
            shap_explanation.append({"feature": "baseline_benign", "value": 1.0, "impact": 0.0})

        shap_explanation = sorted(shap_explanation, key=lambda x: x["impact"], reverse=True)[:10]

        return {
            "threat_type": threat_type,
            "confidence": int(total_score),
            "is_zero_day": is_zero_day,
            "risk_level": risk_level,
            "shap_explanation": shap_explanation,
            "classifier_used": "heuristic_engine",
            "decision_path": decision_path
        }


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="StealthOS Classifier — Step 4")
    parser.add_argument("--features", default=str(RESULTS_DIR / "features.json"))
    parser.add_argument("--behavior", default=str(RESULTS_DIR / "behavior.json"))
    parser.add_argument("--output", default=str(RESULTS_DIR))
    args = parser.parse_args()

    features_path = Path(args.features)
    behavior_path = Path(args.behavior)
    output_dir = Path(args.output)

    if not features_path.exists():
        log.error(f"Features JSON file missing: {features_path}")
        sys.exit(1)
    if not behavior_path.exists():
        log.error(f"Behavior JSON file missing: {behavior_path}")
        sys.exit(1)

    try:
        static_data = json.loads(features_path.read_text(encoding="utf-8"))
        behavior_data = json.loads(behavior_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Failed to read input files: {e}")
        sys.exit(1)

    classifier = StealthClassifier()
    result = classifier.run_classification(static_data, behavior_data)

    output_file = output_dir / "classification_result.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    log.info(f"Classification result saved to {output_file}")

    print("\n" + "=" * 50)
    print("  STEALTHOS — CLASSIFICATION RESULT")
    print("=" * 50)
    print(f"  Threat Type   : {result['threat_type']}")
    print(f"  Confidence    : {result['confidence']}%")
    print(f"  Risk Level    : {result['risk_level']}")
    print(f"  Is Zero-Day   : {result['is_zero_day']}")
    print("\n  Decision Path:")
    for path in result["decision_path"]:
        print(f"    - {path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
