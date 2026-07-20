"""
ABYSS — Model Evaluation Harness
================================
Runs the test set through trained models and outputs real AUC/PR/F1 metrics.
Saves results to evaluation_report.json for comparison.
"""

import json
import numpy as np
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, precision_recall_curve,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import label_binarize

from train_model import Autoencoder
import torch
import torch.nn as nn

# Optional ML imports
try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class ModelEvaluator:
    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)
        self.results = {}
        
    def load_test_data(self):
        """Load vectorized test data."""
        data_dir = Path("ember2018")
        ndim = 2381
        
        y_test = np.memmap(data_dir / "y_test.dat", dtype=np.float32, mode="r")
        n_samples = y_test.shape[0]
        X_test = np.memmap(data_dir / "X_test.dat", dtype=np.float32, mode="r", shape=(n_samples, ndim))
        
        # Filter labeled samples
        test_labeled_mask = (y_test >= 0)
        X_test = X_test[test_labeled_mask]
        y_test = y_test[test_labeled_mask].astype(np.int32)
        
        print(f"Test set: {X_test.shape[0]} samples, {X_test.shape[1]} features")
        print(f"Class distribution: {np.bincount(y_test)}")
        return X_test, y_test
    
    def evaluate_classifier(self, name, model, X_test, y_test, is_onnx=False):
        """Evaluate a binary classifier."""
        if is_onnx:
            input_name = model.get_inputs()[0].name
            outputs = model.run(None, {input_name: X_test.astype(np.float32)})
            y_pred = outputs[0]  # labels
            
            # Handle different probability output formats
            prob_output = outputs[1]
            if isinstance(prob_output, list):
                # RF ONNX returns list of dicts - convert to array
                n_samples = len(prob_output)
                y_prob = np.zeros((n_samples, 2), dtype=np.float32)
                for i, prob_dict in enumerate(prob_output):
                    for cls, prob in prob_dict.items():
                        y_prob[i, int(cls)] = prob
            else:
                y_prob = prob_output  # Already array [batch, classes]
            
            # For AUC we need positive class probability
            y_score = y_prob[:, 1] if y_prob.shape[1] == 2 else y_prob[:, 1]
        else:
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)
            y_score = y_prob[:, 1] if y_prob.shape[1] == 2 else y_prob[:, 1]
        
        # Binary metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_score)
        
        # PR-AUC
        precision, recall, _ = precision_recall_curve(y_test, y_score)
        # precision_recall_curve returns recall in decreasing order, reverse for trapz
        pr_auc = np.trapz(precision[::-1], recall[::-1])
        
        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        
        return {
            "name": name,
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(auc),
            "pr_auc": float(pr_auc),
            "confusion_matrix": cm.tolist(),
            "classification_report": report,
        }
    
    def evaluate_autoencoder(self, model, X_test, y_test, is_onnx=False, threshold=None):
        """Evaluate autoencoder anomaly detection."""
        if is_onnx:
            input_name = model.get_inputs()[0].name
            outputs = model.run(None, {input_name: X_test.astype(np.float32)})
            reconstructions = outputs[0]
        else:
            model.eval()
            with torch.no_grad():
                X_tensor = torch.tensor(X_test, dtype=torch.float32)
                reconstructions = model(X_tensor).numpy()
        
        errors = np.mean((X_test - reconstructions) ** 2, axis=1)
        
        if threshold is None:
            # Use 95th percentile of benign errors as threshold
            benign_errors = errors[y_test == 0]
            threshold = np.percentile(benign_errors, 95)
        
        y_pred = (errors > threshold).astype(int)
        
        # Binary metrics (1 = malicious/anomaly)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        # ROC-AUC using raw error scores
        auc = roc_auc_score(y_test, errors)
        precision, recall, _ = precision_recall_curve(y_test, errors)
        # precision_recall_curve returns recall in decreasing order, reverse for trapz
        pr_auc = np.trapz(precision[::-1], recall[::-1])
        
        return {
            "name": "Autoencoder",
            "threshold": float(threshold),
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(auc),
            "pr_auc": float(pr_auc),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }
    
    def evaluate_ensemble(self, models_dict, X_test, y_test):
        """Evaluate ensemble of multiple models."""
        # Get probabilities from each model
        all_probs = []
        for name, (model, is_onnx) in models_dict.items():
            if is_onnx:
                input_name = model.get_inputs()[0].name
                outputs = model.run(None, {input_name: X_test.astype(np.float32)})
                prob_output = outputs[1]
                
                # Handle different probability output formats
                if isinstance(prob_output, list):
                    # RF ONNX returns list of dicts
                    n_samples = len(prob_output)
                    probs = np.zeros((n_samples, 2), dtype=np.float32)
                    for i, prob_dict in enumerate(prob_output):
                        for cls, prob in prob_dict.items():
                            probs[i, int(cls)] = prob
                else:
                    probs = prob_output
            else:
                probs = model.predict_proba(X_test)
            
            # Handle multi-class - take max probability as confidence
            if probs.shape[1] == 2:
                all_probs.append(probs[:, 1])  # positive class
            else:
                all_probs.append(np.max(probs, axis=1))
        
        # Average ensemble
        ensemble_prob = np.mean(all_probs, axis=0)
        y_pred = (ensemble_prob > 0.5).astype(int)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, ensemble_prob)
        precision, recall, _ = precision_recall_curve(y_test, ensemble_prob)
        pr_auc = np.trapz(precision[::-1], recall[::-1])
        
        return {
            "name": "Ensemble",
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "roc_auc": float(auc),
            "pr_auc": float(pr_auc),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        }
    
    def run_full_evaluation(self):
        """Run complete evaluation suite."""
        print("=" * 60)
        print("  ABYSS MODEL EVALUATION HARNESS")
        print("=" * 60)
        
        X_test, y_test = self.load_test_data()
        
        # Load models
        models = {}
        
        # Pickle models (backward compat)
        import pickle
        rf_path = self.models_dir / "rf_model.pkl"
        xgb_path = self.models_dir / "xgboost_model.pkl"
        lgb_path = self.models_dir / "lightgbm_model.pkl"
        ae_path = self.models_dir / "autoencoder.pt"
        
        if rf_path.exists():
            with open(rf_path, "rb") as f:
                models["rf"] = (pickle.load(f), False)
        if xgb_path.exists():
            with open(xgb_path, "rb") as f:
                models["xgb"] = (pickle.load(f), False)
        if lgb_path.exists():
            with open(lgb_path, "rb") as f:
                models["lgbm"] = (pickle.load(f), False)
        
        # Calibrated models
        rf_cal_path = self.models_dir / "rf_calibrated.pkl"
        xgb_cal_path = self.models_dir / "xgb_calibrated.pkl"
        lgb_cal_path = self.models_dir / "lgb_calibrated.pkl"
        
        if rf_cal_path.exists():
            with open(rf_cal_path, "rb") as f:
                models["rf_cal"] = (pickle.load(f), False)
        if xgb_cal_path.exists():
            with open(xgb_cal_path, "rb") as f:
                models["xgb_cal"] = (pickle.load(f), False)
        if lgb_cal_path.exists():
            with open(lgb_cal_path, "rb") as f:
                models["lgbm_cal"] = (pickle.load(f), False)
        
        # ONNX models (preferred)
        onnx_models = {}
        if HAS_ORT:
            for name, onnx_name in [("rf", "rf_model.onnx"), ("xgb", "xgboost_model.onnx"), ("lgbm", "lightgbm_model.onnx")]:
                onnx_path = self.models_dir / onnx_name
                if onnx_path.exists():
                    onnx_models[name] = (ort.InferenceSession(str(onnx_path)), True)
                    print(f"Loaded ONNX {name} model")
        
        # Autoencoder
        ae_model = None
        ae_onnx = None
        if ae_path.exists():
            # The autoencoder was saved as full model (not state_dict)
            ae_model = torch.load(ae_path, map_location="cpu", weights_only=False)
            ae_model.eval()
        
        onnx_ae_path = self.models_dir / "autoencoder.onnx"
        if HAS_ORT and onnx_ae_path.exists():
            ae_onnx = ort.InferenceSession(str(onnx_ae_path))
        
        print(f"\nLoaded models: {list(models.keys())}")
        print(f"Loaded ONNX models: {list(onnx_models.keys())}")
        print(f"Autoencoder: {'PyTorch' if ae_model else 'None'}, ONNX: {'Yes' if ae_onnx else 'No'}")
        
        # Evaluate individual models
        for name, (model, is_onnx) in {**models, **onnx_models}.items():
            print(f"\nEvaluating {name}...")
            result = self.evaluate_classifier(name, model, X_test, y_test, is_onnx)
            self.results[name] = result
            print(f"  Accuracy: {result['accuracy']:.4f}")
            print(f"  F1: {result['f1']:.4f}")
            print(f"  ROC-AUC: {result['roc_auc']:.4f}")
            print(f"  PR-AUC: {result['pr_auc']:.4f}")
        
        # Evaluate autoencoder
        if ae_model or ae_onnx:
            print("\nEvaluating Autoencoder...")
            ae = ae_onnx if ae_onnx else ae_model
            is_onnx = ae_onnx is not None
            result = self.evaluate_autoencoder(ae, X_test, y_test, is_onnx)
            self.results["autoencoder"] = result
            print(f"  Threshold: {result['threshold']:.6f}")
            print(f"  F1: {result['f1']:.4f}")
            print(f"  ROC-AUC: {result['roc_auc']:.4f}")
            print(f"  PR-AUC: {result['pr_auc']:.4f}")
        
        # Evaluate ensemble
        ensemble_models = {**{k: v for k, v in models.items() if k in ["rf", "xgb", "lgbm", "rf_cal", "xgb_cal", "lgbm_cal"]}, **onnx_models}
        if len(ensemble_models) >= 2:
            print("\nEvaluating Ensemble...")
            result = self.evaluate_ensemble(ensemble_models, X_test, y_test)
            self.results["ensemble"] = result
            print(f"  Accuracy: {result['accuracy']:.4f}")
            print(f"  F1: {result['f1']:.4f}")
            print(f"  ROC-AUC: {result['roc_auc']:.4f}")
            print(f"  PR-AUC: {result['pr_auc']:.4f}")
        
        return self.results
    
    def save_report(self, output_path):
        """Save evaluation report to JSON."""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nReport saved to {output_path}")


def main():
    models_dir = Path("../backend/models")
    evaluator = ModelEvaluator(models_dir)
    evaluator.run_full_evaluation()
    evaluator.save_report(models_dir / "evaluation_report.json")
    
    # Print summary
    print("\n" + "=" * 60)
    print("  EVALUATION SUMMARY")
    print("=" * 60)
    for name, result in evaluator.results.items():
        print(f"  {name:15s} | Acc: {result.get('accuracy', 0):.4f} | F1: {result.get('f1', 0):.4f} | ROC-AUC: {result.get('roc_auc', 0):.4f} | PR-AUC: {result.get('pr_auc', 0):.4f}")


if __name__ == "__main__":
    main()