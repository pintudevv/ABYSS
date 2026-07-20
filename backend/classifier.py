"""
ABYSS — ML & Heuristic Classifier (Step 4)
==============================================
Loads static features (results/features.json) and sandbox behavior (results/behavior.json).
Classifies threat using XGBoost/Random Forest/Autoencoder, falling back to heuristic evaluation.
Outputs classification_result.json in results/ directory.
"""

from __future__ import annotations

import argparse
import hashlib
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
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

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

# ONNX Runtime for fast inference
try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"

# ---------------------------------------------------------------------------
# Model integrity verification
# ---------------------------------------------------------------------------
# Load expected SHA256 hashes from manifest file
def _load_model_hashes() -> dict[str, str]:
    manifest_path = MODELS_DIR / "model_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Extract just the sha256 hash from each model entry
            return {fname: info.get("sha256", "") for fname, info in manifest.get("models", {}).items()}
        except Exception as e:
            log.warning(f"Failed to load model manifest: {e}")
    return {}

MODEL_HASHES = _load_model_hashes()

def verify_model_integrity(model_path: Path, expected_hash: str) -> bool:
    """Verify model file matches expected SHA256 hash. Returns True if valid or no hash configured."""
    if not expected_hash:
        return True  # No hash configured — skip verification (dev mode)
    if not model_path.exists():
        return False
    actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if actual != expected_hash:
        log.error(f"Model integrity check FAILED for {model_path.name}: expected {expected_hash}, got {actual}")
        return False
    return True

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

# Precomputed EMBER feature names (2381 features) - avoids function call overhead per SHAP explanation
EMBER_FEATURE_NAMES = [
    *(f"byte_histogram_{i}" for i in range(256)),
    *(f"byte_entropy_{i}" for i in range(256)),
    *(f"string_info_{i}" for i in range(104)),
    *(f"general_{n}" for n in ["file_size", "has_debug", "exports_count", "imports_count", "has_relocations", "has_resources", "has_signature", "has_tls", "symbols_count", "subsystem"]),
    *(f"header_info_{i}" for i in range(62)),
    *(f"section_info_{i}" for i in range(255)),
    *(f"import_api_hash_{i}" for i in range(1280)),
    *(f"export_api_hash_{i}" for i in range(128)),
    *(f"data_directory_{i}" for i in range(30)),
]

# ---------------------------------------------------------------------------
# Classifier Class
# ---------------------------------------------------------------------------
class StealthClassifier:
    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.xgb_model = None
        self.rf_model = None
        self.lgb_model = None
        self.xgb_cal = None
        self.rf_cal = None
        self.lgb_cal = None
        self.autoencoder = None
        # ONNX Runtime sessions (fast inference)
        self.xgb_ort = None
        self.rf_ort = None
        self.lgb_ort = None
        self.ae_ort = None
        self.is_ml_loaded = False
        self._shap_explainer = None  # Cached SHAP TreeExplainer
        self._load_models()

    def _load_models(self):
        xgb_path = self.models_dir / "xgboost_model.pkl"
        rf_path = self.models_dir / "rf_model.pkl"
        lgb_path = self.models_dir / "lightgbm_model.pkl"
        # Calibrated models
        xgb_cal_path = self.models_dir / "xgb_calibrated.pkl"
        rf_cal_path = self.models_dir / "rf_calibrated.pkl"
        lgb_cal_path = self.models_dir / "lgb_calibrated.pkl"
        ae_path = self.models_dir / "autoencoder.pt"
        ae_scaler_path = self.models_dir / "ae_scaler.pkl"
        # ONNX paths
        xgb_onnx_path = self.models_dir / "xgboost_model.onnx"
        rf_onnx_path = self.models_dir / "rf_model.onnx"
        lgb_onnx_path = self.models_dir / "lightgbm_model.onnx"
        ae_onnx_path = self.models_dir / "autoencoder.onnx"

        try:
            # Verify model integrity before loading (prevents pickle RCE)
            for model_path, expected_hash in [
                (xgb_path, MODEL_HASHES.get("xgboost_model.pkl", "")),
                (rf_path, MODEL_HASHES.get("rf_model.pkl", "")),
                (lgb_path, MODEL_HASHES.get("lightgbm_model.pkl", "")),
                (ae_path, MODEL_HASHES.get("autoencoder.pt", "")),
            ]:
                if model_path.exists() and not verify_model_integrity(model_path, expected_hash):
                    log.error(f"Model integrity check failed for {model_path.name} — refusing to load")
                    return  # Abort all model loading on integrity failure

            # Load pickle models (backward compatibility)
            if xgb_path.exists():
                with open(xgb_path, "rb") as f:
                    self.xgb_model = pickle.load(f)
                log.info("XGBoost model loaded successfully")
            if rf_path.exists():
                with open(rf_path, "rb") as f:
                    self.rf_model = pickle.load(f)
                log.info("Random Forest model loaded successfully")
            if lgb_path.exists():
                with open(lgb_path, "rb") as f:
                    self.lgb_model = pickle.load(f)
                log.info("LightGBM model loaded successfully")
            
            # Load calibrated models (preferred for inference)
            if xgb_cal_path.exists():
                with open(xgb_cal_path, "rb") as f:
                    self.xgb_cal = pickle.load(f)
                log.info("XGBoost calibrated model loaded")
            if rf_cal_path.exists():
                with open(rf_cal_path, "rb") as f:
                    self.rf_cal = pickle.load(f)
                log.info("Random Forest calibrated model loaded")
            if lgb_cal_path.exists():
                with open(lgb_cal_path, "rb") as f:
                    self.lgb_cal = pickle.load(f)
                log.info("LightGBM calibrated model loaded")
            
            if ae_path.exists() and HAS_TORCH:
                # Define Autoencoder class structure so PyTorch can unpickle it (NEW architecture)
                class Autoencoder(nn.Module):
                    def __init__(self):
                        super().__init__()
                        self.encoder = nn.Sequential(
                            nn.Linear(2381, 512),
                            nn.ReLU(),
                            nn.BatchNorm1d(512),
                            nn.Linear(512, 128),
                            nn.ReLU(),
                            nn.BatchNorm1d(128),
                            nn.Linear(128, 32),
                            nn.ReLU()
                        )
                        self.decoder = nn.Sequential(
                            nn.Linear(32, 128),
                            nn.ReLU(),
                            nn.BatchNorm1d(128),
                            nn.Linear(128, 512),
                            nn.ReLU(),
                            nn.BatchNorm1d(512),
                            nn.Linear(512, 2381)
                        )
                    def forward(self, x):
                        return self.decoder(self.encoder(x))
                
                # Import Autoencoder into global namespace so unpickler resolves it
                import sys
                sys.modules['__main__'].Autoencoder = Autoencoder
                
                self.autoencoder = torch.load(str(ae_path), weights_only=False)
                log.info("PyTorch Autoencoder model loaded successfully")
                
                # Load scaler for autoencoder
                if ae_scaler_path.exists():
                    self.ae_scaler = joblib.load(ae_scaler_path)
                    log.info("Autoencoder scaler loaded")
            
            # Load ONNX models for fast inference (preferred path)
            if HAS_ORT:
                if xgb_onnx_path.exists():
                    try:
                        self.xgb_ort = ort.InferenceSession(str(xgb_onnx_path), providers=['CPUExecutionProvider'])
                        log.info("XGBoost ONNX model loaded for fast inference")
                    except Exception as e:
                        log.warning(f"Failed to load XGBoost ONNX: {e}")
                if rf_onnx_path.exists():
                    try:
                        self.rf_ort = ort.InferenceSession(str(rf_onnx_path), providers=['CPUExecutionProvider'])
                        log.info("Random Forest ONNX model loaded for fast inference")
                    except Exception as e:
                        log.warning(f"Failed to load RF ONNX: {e}")
                if lgb_onnx_path.exists():
                    try:
                        self.lgb_ort = ort.InferenceSession(str(lgb_onnx_path), providers=['CPUExecutionProvider'])
                        log.info("LightGBM ONNX model loaded for fast inference")
                    except Exception as e:
                        log.warning(f"Failed to load LightGBM ONNX: {e}")
                if ae_onnx_path.exists():
                    try:
                        self.ae_ort = ort.InferenceSession(str(ae_onnx_path), providers=['CPUExecutionProvider'])
                        log.info("Autoencoder ONNX model loaded for fast inference")
                    except Exception as e:
                        log.warning(f"Failed to load Autoencoder ONNX: {e}")
            
            # Initialize SHAP explainer once (cached) if XGBoost loaded
            if self.xgb_model:
                import shap
                self._shap_explainer = shap.TreeExplainer(self.xgb_model)
                log.info("SHAP TreeExplainer initialized and cached")
            
            if self.xgb_model or self.rf_model or self.lgb_model or self.xgb_cal or self.rf_cal or self.lgb_cal or self.autoencoder or self.xgb_ort or self.rf_ort or self.lgb_ort or self.ae_ort:
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

                # 3. Perform model predictions (prefer ONNX Runtime for speed)
                # Use calibrated models when available for better probability calibration
                xgb_model = self.xgb_cal if self.xgb_cal else self.xgb_model
                rf_model = self.rf_cal if self.rf_cal else self.rf_model
                lgb_model = self.lgb_cal if self.lgb_cal else self.lgb_model
                
                if self.xgb_ort:
                    # XGBoost ONNX inference
                    xgb_onnx_input = {self.xgb_ort.get_inputs()[0].name: features_vec}
                    xgb_onnx_output = self.xgb_ort.run(None, xgb_onnx_input)
                    xgb_prob = xgb_onnx_output[1][0]  # [batch, classes]
                    xgb_pred = int(np.argmax(xgb_prob))
                else:
                    xgb_pred = int(xgb_model.predict(features_vec)[0])
                    xgb_prob = xgb_model.predict_proba(features_vec)[0]
                
                if self.rf_ort:
                    # Random Forest ONNX inference
                    rf_onnx_input = {self.rf_ort.get_inputs()[0].name: features_vec}
                    rf_onnx_output = self.rf_ort.run(None, rf_onnx_input)
                    rf_prob = rf_onnx_output[1][0]
                    rf_pred = int(np.argmax(rf_prob))
                else:
                    rf_pred = int(rf_model.predict(features_vec)[0])
                    rf_prob = rf_model.predict_proba(features_vec)[0]

                if self.lgb_ort:
                    # LightGBM ONNX inference
                    lgb_onnx_input = {self.lgb_ort.get_inputs()[0].name: features_vec}
                    lgb_onnx_output = self.lgb_ort.run(None, lgb_onnx_input)
                    lgb_prob = lgb_onnx_output[1][0]
                    lgb_pred = int(np.argmax(lgb_prob))
                else:
                    lgb_pred = int(lgb_model.predict(features_vec)[0])
                    lgb_prob = lgb_model.predict_proba(features_vec)[0]

                # 4. Perform Autoencoder reconstruction (ONNX or PyTorch)
                # Apply scaler if available (for new autoencoder architecture)
                ae_input = features_vec
                if hasattr(self, 'ae_scaler') and self.ae_scaler is not None:
                    ae_input = self.ae_scaler.transform(features_vec)
                
                if self.ae_ort:
                    ae_onnx_input = {self.ae_ort.get_inputs()[0].name: ae_input}
                    ae_onnx_output = self.ae_ort.run(None, ae_onnx_input)
                    ae_reconstructed = ae_onnx_output[0]
                    ae_loss = float(np.mean((ae_input - ae_reconstructed)**2))
                else:
                    ae_tensor = torch.tensor(ae_input, dtype=torch.float32)
                    self.autoencoder.eval()
                    with torch.no_grad():
                        ae_reconstructed = self.autoencoder(ae_tensor)
                        ae_loss = float(torch.mean((ae_tensor - ae_reconstructed)**2).item())

                # Zero-Day anomaly detection: threshold from normalized training (~4.5)
                is_zero_day = ae_loss > 4.5
                
                # 5. Compute real SHAP explanation values using cached TreeExplainer
                raw_shap = self._shap_explainer.shap_values(features_vec)
                # For binary classifications, TreeExplainer returns shape (1, 2381) or (1, 2381, 2)
                if isinstance(raw_shap, list):
                    # Newer shap returns list for multi-class/binary outputs
                    shap_vec = raw_shap[1][0] if len(raw_shap) > 1 else raw_shap[0][0]
                elif len(raw_shap.shape) == 3:
                    shap_vec = raw_shap[0, :, 1]
                else:
                    shap_vec = raw_shap[0]

                # Map feature indices to names using precomputed array
                shap_explanation = []
                for idx, val in enumerate(shap_vec):
                    if abs(val) > 1e-5:
                        shap_explanation.append({
                            "feature": EMBER_FEATURE_NAMES[idx],
                            "value": float(features_vec[0, idx]),
                            "impact": float(val)
                        })

                # Sort by absolute impact
                shap_explanation = sorted(shap_explanation, key=lambda x: abs(x["impact"]), reverse=True)[:10]

                # 6. Blending with Heuristics & Behavior
                decision_path = [
                    f"XGBoost Classifier predicts class {xgb_pred} (malicious probability: {xgb_prob[1]*100:.1f}%)",
                    f"Random Forest Classifier predicts class {rf_pred} (malicious probability: {rf_prob[1]*100:.1f}%)",
                    f"LightGBM Classifier predicts class {lgb_pred} (malicious probability: {lgb_prob[1]*100:.1f}%)",
                    f"Autoencoder Reconstruction Loss: {ae_loss:.4f} (Zero-Day: {is_zero_day})"
                ]

                # Combine ML scores with behavior (Frida api hooks, registry persistences, network blocks)
                behavior_result = self._evaluate_heuristics(static_data, behavior_data)
                
                # final score is a blend of XGB/RF/LGBM predictions and dynamic indicators
                ml_score = max(xgb_prob[1], rf_prob[1], lgb_prob[1]) * 100
                
                # Static heuristic score (from static analysis)
                static_heuristic_score = behavior_result["confidence"]
                static_risk_level = "CLEAN"
                if static_heuristic_score >= 85: static_risk_level = "CRITICAL"
                elif static_heuristic_score >= 60: static_risk_level = "HIGH"
                elif static_heuristic_score >= 35: static_risk_level = "MEDIUM"
                elif static_heuristic_score >= 15: static_risk_level = "LOW"
                
                # If all ML models say benign, DON'T ignore strong static heuristics
                if xgb_pred == 0 and rf_pred == 0 and lgb_pred == 0:
                    # If static heuristics indicate MEDIUM or HIGH risk, trust them over ML
                    if static_heuristic_score >= 50:
                        total_score = int(min(static_heuristic_score + ml_score * 0.3, 100))
                        threat_type = behavior_result["threat_type"]
                        decision_path.append(f"ML models benign but static heuristics indicate {static_risk_level} risk ({static_heuristic_score}/100) — prioritizing static analysis.")
                    elif static_heuristic_score >= 15:
                        # Low-Medium heuristic: blend but don't ignore
                        total_score = int(min(static_heuristic_score * 0.7 + ml_score * 0.3, 100))
                        threat_type = behavior_result["threat_type"] or "Suspicious"
                        decision_path.append(f"ML models benign; static heuristics {static_risk_level} ({static_heuristic_score}/100) — blended score.")
                    else:
                        if behavior_result["confidence"] < 60:
                            total_score = int(min(ml_score, 15))
                            threat_type = "Clean"
                            decision_path.append("ML models predict benign; low-severity heuristics ignored.")
                        else:
                            total_score = int(min(ml_score + behavior_result["confidence"] * 0.5, 100))
                            threat_type = behavior_result["threat_type"]
                else:
                    # At least one ML model says malicious: blend with heuristics
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
# Dynamic + Final verdict builders
# ---------------------------------------------------------------------------

def _build_dynamic_verdict(behavior_data: dict, dynamic_skipped: bool,
                            skip_reason: str | None) -> dict:
    """Extract behavioral data into a structured dynamic verdict."""
    if dynamic_skipped:
        return {"dynamic_skipped": True, "skip_reason": skip_reason}

    is_simulated = behavior_data.get("is_simulated", False)
    api_calls = behavior_data.get("api_calls", [])
    api_names = {call.get("api", "") for call in api_calls}

    return {
        "dynamic_skipped": False,
        "is_simulated": is_simulated,
        "analysis_duration_seconds": behavior_data.get("analysis_duration_seconds", 0),
        "api_calls": api_calls,
        "file_operations": behavior_data.get("file_operations", []),
        "processes": behavior_data.get("processes", []),
        "network_connections": behavior_data.get("network_connections", []),
        "registry_operations": behavior_data.get("registry_operations", []),
        "score": behavior_data.get("score", 0),
        "behavioral_indicators": {
            "trojan_apis":     sorted(api_names & TROJAN_APIS),
            "ransomware_apis": sorted(api_names & RANSOMWARE_APIS),
            "spyware_apis":    sorted(api_names & SPYWARE_APIS),
            "network_apis":    sorted(api_names & NETWORK_APIS),
        },
    }


def _build_final_verdict(ml_result: dict, dynamic_verdict: dict) -> dict:
    """Combine ML verdict + dynamic behavioral indicators into one final verdict."""
    ml_confidence = ml_result.get("confidence", 0)
    ml_threat     = ml_result.get("threat_type", "Clean")
    reasoning     = [
        f"ML ({ml_result.get('classifier_used', 'heuristic')}): "
        f"{ml_threat} at {ml_confidence}% confidence"
    ]

    threat_type    = ml_threat
    final_conf     = ml_confidence
    dynamic_boost  = 0

    if not dynamic_verdict.get("dynamic_skipped", True):
        ind = dynamic_verdict.get("behavioral_indicators", {})
        trojan_hits  = ind.get("trojan_apis", [])
        ransom_hits  = ind.get("ransomware_apis", [])
        spyware_hits = ind.get("spyware_apis", [])

        if trojan_hits:
            dynamic_boost += min(len(trojan_hits) * 10, 20)
            reasoning.append(f"Dynamic — trojan APIs: {trojan_hits}")
            if threat_type == "Clean":
                threat_type = "Trojan"
        if ransom_hits:
            dynamic_boost += min(len(ransom_hits) * 10, 20)
            reasoning.append(f"Dynamic — ransomware APIs: {ransom_hits}")
            if threat_type == "Clean":
                threat_type = "Ransomware"
        if spyware_hits:
            dynamic_boost += min(len(spyware_hits) * 10, 20)
            reasoning.append(f"Dynamic — spyware APIs: {spyware_hits}")
            if threat_type == "Clean":
                threat_type = "Spyware"

        api_count = len(dynamic_verdict.get("api_calls", []))
        reasoning.append(f"Dynamic — {api_count} API call(s) captured by Frida hooks")
        final_conf = min(ml_confidence + dynamic_boost, 100)
    else:
        reasoning.append(f"Dynamic — {dynamic_verdict.get('skip_reason', 'skipped')}")

    # Risk level from final confidence
    if final_conf >= 85:   risk_level = "CRITICAL"
    elif final_conf >= 60: risk_level = "HIGH"
    elif final_conf >= 35: risk_level = "MEDIUM"
    elif final_conf >= 15: risk_level = "LOW"
    else:                  risk_level = "CLEAN"

    label = ("benign" if (threat_type == "Clean" or final_conf < 15)
             else "suspicious" if final_conf < 40
             else "malicious")

    return {
        "label":      label,
        "confidence": final_conf,
        "threat_type": threat_type,
        "risk_level":  risk_level,
        "is_zero_day": ml_result.get("is_zero_day", False),
        "reasoning":   " | ".join(reasoning),
    }


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main():
    import hashlib
    from datetime import datetime as _dt

    parser = argparse.ArgumentParser(description="ABYSS Classifier — Step 4")
    parser.add_argument("file", nargs="?", default=None,
                        help="File to analyse (optional — used to run static analysis if features.json missing)")
    parser.add_argument("--features", default=str(RESULTS_DIR / "features.json"))
    parser.add_argument("--behavior", default=str(RESULTS_DIR / "behavior.json"))
    parser.add_argument("--output",   default=str(RESULTS_DIR))
    args = parser.parse_args()

    features_path = Path(args.features)
    behavior_path = Path(args.behavior)
    output_dir    = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # If a file was given, run static_analysis.py when features.json is missing
    # OR when features.json was computed for a *different* file (fixes the filepath quirk).
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            log.error(f"File not found: {file_path}")
            sys.exit(1)
        features_match = False
        if features_path.exists():
            try:
                _existing = json.loads(features_path.read_text(encoding="utf-8"))
                _stored_fp = _existing.get("file_info", {}).get("filepath", "")
                features_match = Path(_stored_fp).resolve() == file_path.resolve()
            except Exception:
                pass
        if not features_match:
            log.info(f"Running static_analysis.py for {file_path.name} (features.json mismatch or missing)...")
            import subprocess as _sp
            _r = _sp.run(
                [sys.executable, str(BASE_DIR / "static_analysis.py"),
                 str(file_path), "--output", str(output_dir)],
                capture_output=True, text=True
            )
            if _r.returncode != 0:
                log.warning(f"static_analysis.py exited {_r.returncode}: {_r.stderr[:300]}")

    if not features_path.exists():
        log.error(f"Features JSON missing: {features_path}")
        sys.exit(1)

    try:
        static_data = json.loads(features_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Cannot read features.json: {e}")
        sys.exit(1)

    # ---- Non-PE files: use heuristic results directly, skip ML models ----
    file_type_info = static_data.get("file_type", {})
    is_pe = file_type_info.get("is_pe", True)  # default True for backwards compat
    is_pdf = file_type_info.get("is_pdf", False)
    is_zip = file_type_info.get("is_zip", False)

    if is_pdf or is_zip or not is_pe:
        fi   = static_data.get("file_info", {})
        risk = static_data.get("heuristic_risk", {})
        score     = risk.get("score", 0)
        risk_lvl  = risk.get("risk_level", "CLEAN")
        file_kind = "PDF" if is_pdf else "ZIP" if is_zip else "Unknown"

        # Map heuristic score to threat type
        if score >= 60:
            threat_type = f"Malicious {file_kind}"
        elif score >= 30:
            threat_type = f"Suspicious {file_kind}"
        else:
            threat_type = "Clean"

        label = "malicious" if score >= 40 else "clean"

        unified = {
            "file":               fi.get("filename", "unknown"),
            "sha256":             fi.get("sha256", ""),
            "analysis_timestamp": fi.get("analysis_timestamp", _dt.utcnow().isoformat() + "Z"),
            "ml_verdict": {
                "threat_type":     threat_type,
                "confidence":      score,
                "is_zero_day":     False,
                "risk_level":      risk_lvl,
                "shap_explanation": [],
                "classifier_used": "heuristic",
                "decision_path":   risk.get("reasons", []),
            },
            "dynamic_verdict": {
                "dynamic_skipped": True,
                "skip_reason":     f"Non-PE file ({file_kind}) — sandbox not applicable",
                "mock_mode":       False,
                "api_calls":       [],
                "file_operations": [],
                "processes":       [],
                "network_connections": [],
                "registry_operations": [],
                "score": 0,
                "behavioral_indicators": {},
            },
            "final_verdict": {
                "label":       label,
                "confidence":  score,
                "threat_type": threat_type,
                "risk_level":  risk_lvl,
                "is_zero_day": False,
                "reasoning":   f"Heuristic {file_kind} analysis: {score}/100 score. " + "; ".join(risk.get("reasons", [])),
            },
        }
        out_path = output_dir / "classification_result.json"
        out_path.write_text(json.dumps(unified, indent=2), encoding="utf-8")
        log.info(f"Non-PE classification complete: {threat_type} ({score}%) → {out_path}")
        print(f"\n  {file_kind} verdict: {threat_type} | Score: {score}/100 [{risk_lvl}]")
        sys.exit(0)

    # ---- Load behavior.json — reject mock data, skip cleanly if absent ----
    dynamic_skipped   = False
    dynamic_skip_reason: str | None = None
    behavior_data: dict = {}

    if not behavior_path.exists():
        dynamic_skipped    = True
        dynamic_skip_reason = "behavior.json not found — sandbox was not run"
        log.info("behavior.json absent — dynamic_verdict will be skipped")
    else:
        try:
            raw_behavior = json.loads(behavior_path.read_text(encoding="utf-8"))
        except Exception as e:
            log.error(f"Cannot read behavior.json: {e}")
            sys.exit(1)

        if raw_behavior.get("mock_mode", False):
            # Use simulated data for heuristic analysis but mark as simulated
            # This allows heuristic analysis on simulated behavior when real sandbox unavailable
            behavior_data = raw_behavior
            behavior_data["is_simulated"] = True
            log.info(f"behavior.json is simulated — using for heuristic analysis only "
                     f"({len(behavior_data.get('api_calls', []))} API call(s))")
        else:
            behavior_data = raw_behavior
            log.info(f"behavior.json loaded — mock_mode=False, "
                     f"{len(behavior_data.get('api_calls', []))} API call(s)")

    # ---- ML classification ----
    classifier = StealthClassifier()
    ml_verdict = classifier.run_classification(static_data, behavior_data)

    # ---- Dynamic verdict ----
    dynamic_verdict = _build_dynamic_verdict(behavior_data, dynamic_skipped, dynamic_skip_reason)

    # ---- Final combined verdict ----
    final_verdict = _build_final_verdict(ml_verdict, dynamic_verdict)

    # ---- Build unified output ----
    file_name = Path(args.file).name if args.file else "unknown"
    file_hash = ""
    if args.file:
        fp = Path(args.file)
        if fp.exists():
            with open(fp, "rb") as fh:
                file_hash = hashlib.sha256(fh.read()).hexdigest()

    unified = {
        "file":               file_name,
        "sha256":             file_hash,
        "analysis_timestamp": _dt.utcnow().isoformat() + "Z",
        "ml_verdict":         ml_verdict,
        "dynamic_verdict":    dynamic_verdict,
        "final_verdict":      final_verdict,
    }

    out_path = output_dir / "classification_result.json"
    out_path.write_text(json.dumps(unified, indent=2), encoding="utf-8")
    log.info(f"Unified result → {out_path}")

    # ---- Print summary ----
    dv = dynamic_verdict
    fv = final_verdict
    mv = ml_verdict
    print("\n" + "=" * 60)
    print("  ABYSS — UNIFIED CLASSIFICATION RESULT")
    print("=" * 60)
    print(f"  File          : {file_name}")
    if file_hash:
        print(f"  SHA-256       : {file_hash[:16]}...")
    print()
    print("  ML VERDICT:")
    print(f"    Threat Type : {mv['threat_type']}")
    print(f"    Confidence  : {mv['confidence']}%")
    print(f"    Risk Level  : {mv['risk_level']}")
    print(f"    Classifier  : {mv['classifier_used']}")
    print()
    print("  DYNAMIC VERDICT:")
    if dv.get("dynamic_skipped"):
        print(f"    Status      : SKIPPED — {dv.get('skip_reason')}")
    else:
        print(f"    API Calls   : {len(dv.get('api_calls', []))}")
        print(f"    File Ops    : {len(dv.get('file_operations', []))}")
        print(f"    Processes   : {len(dv.get('processes', []))}")
        ind = dv.get("behavioral_indicators", {})
        for k, v in ind.items():
            if v:
                print(f"    {k.replace('_', ' ').title()}: {v}")
    print()
    print("  FINAL VERDICT:")
    print(f"    Label       : {fv['label'].upper()}")
    print(f"    Confidence  : {fv['confidence']}%")
    print(f"    Threat Type : {fv['threat_type']}")
    print(f"    Risk Level  : {fv['risk_level']}")
    print(f"    Reasoning   : {fv['reasoning']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

