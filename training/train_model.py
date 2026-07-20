"""
StealthOS — Real EMBER Model Training Script (Step 2)
=====================================================
Trains supervised models (RF, XGBoost, LightGBM) and unsupervised anomaly model (PyTorch Autoencoder)
using the real vectorized EMBER 2018 dataset (2381 features).
Saves trained binaries to backend/models/ directory.
Exports ONNX models for fast inference with ONNX Runtime.
"""

from __future__ import annotations

import json
import os
import pickle
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
import xgboost as xgb
import lightgbm as lgb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import joblib

# ONNX export
try:
    import onnx
    import onnxruntime as ort
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    print("WARNING: ONNX export not available. Install: pip install onnx onnxruntime skl2onnx")

# Try to import onnxmltools for XGBoost ONNX export
try:
    import onnxmltools
    HAS_ONNXMLTOOLS = True
except ImportError:
    HAS_ONNXMLTOOLS = False
    print("WARNING: onnxmltools not available. XGBoost ONNX export may fail. Install: pip install onnxmltools")

# LightGBM ONNX export
try:
    from onnxmltools.convert import convert_lightgbm
    HAS_LGBM_ONNX = True
except ImportError:
    HAS_LGBM_ONNX = False
    print("WARNING: LightGBM ONNX export not available.")

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

# Fix random seed for reproducibility
np.random.seed(42)
torch.manual_seed(42)

def main():
    data_dir = Path("ember2018")
    models_dir = Path("../backend/models")
    models_dir.mkdir(exist_ok=True)

    print("Loading vectorized EMBER dataset...")
    # Read the shapes based on files
    ndim = 2381
    X_train_path = data_dir / "X_train.dat"
    y_train_path = data_dir / "y_train.dat"
    X_test_path = data_dir / "X_test.dat"
    y_test_path = data_dir / "y_test.dat"

    y_train = np.memmap(y_train_path, dtype=np.float32, mode="r")
    N_train = y_train.shape[0]
    X_train = np.memmap(X_train_path, dtype=np.float32, mode="r", shape=(N_train, ndim))

    y_test = np.memmap(y_test_path, dtype=np.float32, mode="r")
    N_test = y_test.shape[0]
    X_test = np.memmap(X_test_path, dtype=np.float32, mode="r", shape=(N_test, ndim))

    print(f"X_train shape: {X_train.shape} | y_train shape: {y_train.shape}")
    print(f"X_test shape: {X_test.shape} | y_test shape: {y_test.shape}")

    # 1. Filter out unlabeled samples (-1) for supervised classifiers
    train_labeled_mask = (y_train >= 0)
    X_train_sup = X_train[train_labeled_mask]
    y_train_sup = y_train[train_labeled_mask].astype(np.int32)

    test_labeled_mask = (y_test >= 0)
    X_test_sup = X_test[test_labeled_mask]
    y_test_sup = y_test[test_labeled_mask].astype(np.int32)

    print(f"Filtered Supervised Train: {X_train_sup.shape[0]} samples")
    print(f"Filtered Supervised Test: {X_test_sup.shape[0]} samples")

    # 2. Train Random Forest Classifier
    print("Training Random Forest Classifier on real EMBER data...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=15, n_jobs=-1, random_state=42)
    rf.fit(X_train_sup, y_train_sup)

    rf_preds = rf.predict(X_test_sup)
    rf_acc = accuracy_score(y_test_sup, rf_preds)
    print("\n" + "=" * 50)
    print("  RANDOM FOREST EVALUATION ON REAL EMBER TEST SET")
    print("=" * 50)
    print(f"  Accuracy: {rf_acc * 100:.4f}%")
    print(classification_report(y_test_sup, rf_preds, digits=4))
    print("  Confusion Matrix:")
    print(confusion_matrix(y_test_sup, rf_preds))
    if rf_acc > 0.999:
        print("  WARNING: Random Forest accuracy is suspiciously close to 100%. Check for train/test data leak!")
    print("=" * 50)

    # 3. Train XGBoost Classifier
    print("\nTraining XGBoost Classifier on real EMBER data...")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        n_jobs=-1,
        random_state=42
    )
    xgb_clf.fit(X_train_sup, y_train_sup)

    xgb_preds = xgb_clf.predict(X_test_sup)
    xgb_acc = accuracy_score(y_test_sup, xgb_preds)
    print("\n" + "=" * 50)
    print("  XGBOOST EVALUATION ON REAL EMBER TEST SET")
    print("=" * 50)
    print(f"  Accuracy: {xgb_acc * 100:.4f}%")
    print(classification_report(y_test_sup, xgb_preds, digits=4))
    print("  Confusion Matrix:")
    print(confusion_matrix(y_test_sup, xgb_preds))
    if xgb_acc > 0.999:
        print("  WARNING: XGBoost accuracy is suspiciously close to 100%. Check for train/test data leak!")
    print("=" * 50)

    # 4. Train LightGBM Classifier (EMBER's native model)
    print("\nTraining LightGBM Classifier on real EMBER data...")
    lgb_clf = lgb.LGBMClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        num_leaves=63,
        n_jobs=-1,
        random_state=42,
        verbosity=-1
    )
    lgb_clf.fit(X_train_sup, y_train_sup)

    lgb_preds = lgb_clf.predict(X_test_sup)
    lgb_acc = accuracy_score(y_test_sup, lgb_preds)
    print("\n" + "=" * 50)
    print("  LIGHTGBM EVALUATION ON REAL EMBER TEST SET")
    print("=" * 50)
    print(f"  Accuracy: {lgb_acc * 100:.4f}%")
    print(classification_report(y_test_sup, lgb_preds, digits=4))
    print("  Confusion Matrix:")
    print(confusion_matrix(y_test_sup, lgb_preds))
    if lgb_acc > 0.999:
        print("  WARNING: LightGBM accuracy is suspiciously close to 100%. Check for train/test data leak!")
    print("=" * 50)

    # 5. Train PyTorch Autoencoder (trained only on Benign class 0)
    print("\nTraining PyTorch Autoencoder on Benign EMBER data...")
    X_train_clean = X_train[y_train == 0].astype(np.float32)
    
    # Normalize features for better autoencoder training
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train_clean_scaled = scaler.fit_transform(X_train_clean)
    X_test_sup_scaled = scaler.transform(X_test_sup)
    
    # Save scaler for inference
    import joblib
    joblib.dump(scaler, models_dir / "ae_scaler.pkl")
    
    # Custom Autoencoder definition with 2381 inputs
    train_dataset = TensorDataset(torch.tensor(X_train_clean_scaled, dtype=torch.float32))
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True)

    ae = Autoencoder()
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(ae.parameters(), lr=1e-3, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=30, eta_min=1e-5)

    ae.train()
    for epoch in range(30):
        epoch_loss = 0.0
        for batch in train_loader:
            x_batch = batch[0]
            optimizer.zero_grad()
            outputs = ae(x_batch)
            loss = criterion(outputs, x_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(ae.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item() * x_batch.size(0)
        scheduler.step()
        print(f"  Epoch {epoch+1:2d}/30 | MSE Loss: {epoch_loss / len(X_train_clean_scaled):.6f} | LR: {optimizer.param_groups[0]['lr']:.2e}")

    # Evaluate Autoencoder on Test Set (FPR / TPR)
    ae.eval()
    with torch.no_grad():
        X_test_clean_scaled = X_test_sup_scaled[y_test_sup == 0]
        X_test_mal_scaled = X_test_sup_scaled[y_test_sup == 1]
        
        clean_tensors = torch.tensor(X_test_clean_scaled, dtype=torch.float32)
        mal_tensors = torch.tensor(X_test_mal_scaled, dtype=torch.float32)
        
        clean_errors = torch.mean((clean_tensors - ae(clean_tensors))**2, dim=1).numpy()
        mal_errors = torch.mean((mal_tensors - ae(mal_tensors))**2, dim=1).numpy()

    threshold = np.percentile(clean_errors, 95)
    ae_fpr = np.mean(clean_errors > threshold)
    ae_tpr = np.mean(mal_errors > threshold)
    
    # --- Probability Calibration (Platt Scaling) ---
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
    
    print("\n" + "=" * 50)
    print("  PROBABILITY CALIBRATION (Platt Scaling)")
    print("=" * 50)
    
    # Split training data for calibration (use 20% holdout)
    n_train = len(X_train_sup)
    cal_split = int(n_train * 0.8)
    indices = np.random.permutation(n_train)
    train_idx, cal_idx = indices[:cal_split], indices[cal_split:]
    
    X_train_cal = X_train_sup[train_idx]
    y_train_cal = y_train_sup[train_idx]
    X_cal = X_train_sup[cal_idx]
    y_cal = y_train_sup[cal_idx]
    
    # Retrain models on 80% for calibration
    rf_cal = RandomForestClassifier(n_estimators=100, max_depth=15, n_jobs=-1, random_state=42)
    rf_cal.fit(X_train_cal, y_train_cal)
    
    xgb_cal = xgb.XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, n_jobs=-1, random_state=42)
    xgb_cal.fit(X_train_cal, y_train_cal)
    
    lgb_cal = lgb.LGBMClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, num_leaves=63, n_jobs=-1, random_state=42, verbosity=-1)
    lgb_cal.fit(X_train_cal, y_train_cal)
    
    # Calibrate with Platt scaling (sigmoid)
    rf_calibrated = CalibratedClassifierCV(rf_cal, method='sigmoid', cv='prefit')
    rf_calibrated.fit(X_cal, y_cal)
    
    xgb_calibrated = CalibratedClassifierCV(xgb_cal, method='sigmoid', cv='prefit')
    xgb_calibrated.fit(X_cal, y_cal)
    
    lgb_calibrated = CalibratedClassifierCV(lgb_cal, method='sigmoid', cv='prefit')
    lgb_calibrated.fit(X_cal, y_cal)
    
    # Evaluate calibration on test set
    from sklearn.metrics import brier_score_loss
    
    for name, orig, cal in [
        ("RF", rf, rf_calibrated),
        ("XGB", xgb_clf, xgb_calibrated),
        ("LGBM", lgb_clf, lgb_calibrated)
    ]:
        orig_probs = orig.predict_proba(X_test_sup)[:, 1]
        cal_probs = cal.predict_proba(X_test_sup)[:, 1]
        
        orig_brier = brier_score_loss(y_test_sup, orig_probs)
        cal_brier = brier_score_loss(y_test_sup, cal_probs)
        
        orig_auc = roc_auc_score(y_test_sup, orig_probs)
        cal_auc = roc_auc_score(y_test_sup, cal_probs)
        
        print(f"  {name}: Brier {orig_brier:.6f} -> {cal_brier:.6f} | AUC {orig_auc:.6f} -> {cal_auc:.6f}")
    
    # Save calibrated models (for pickle inference)
    with open(models_dir / "rf_calibrated.pkl", "wb") as f:
        pickle.dump(rf_calibrated, f)
    with open(models_dir / "xgb_calibrated.pkl", "wb") as f:
        pickle.dump(xgb_calibrated, f)
    with open(models_dir / "lgb_calibrated.pkl", "wb") as f:
        pickle.dump(lgb_calibrated, f)
    print("  Calibrated models saved.")

    # Keep original models for ONNX export (CalibratedClassifierCV not supported)
    # rf, xgb_clf, lgb_clf remain unchanged

    print("\n" + "=" * 50)
    print("  AUTOENCODER ANOMALY DETECTION EVALUATION")
    print("=" * 50)
    print(f"  Anomaly Threshold (95th % clean): {threshold:.6f}")
    print(f"  False Positive Rate (FPR)       : {ae_fpr * 100:.2f}%")
    print(f"  True Positive Rate (TPR)        : {ae_tpr * 100:.2f}%")
    print("=" * 50)

    # Save evaluation metrics
    metrics = {
        "timestamp": "2026-07-18",
        "dataset": "EMBER 2018",
        "train_samples": int(X_train_sup.shape[0]),
        "test_samples": int(X_test_sup.shape[0]),
        "random_forest": {
            "accuracy": float(rf_acc),
            "n_estimators": 100,
            "max_depth": 15,
        },
        "xgboost": {
            "accuracy": float(xgb_acc),
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
        },
        "lightgbm": {
            "accuracy": float(lgb_acc),
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "num_leaves": 63,
        },
        "autoencoder": {
            "threshold_95th_percentile": float(threshold),
            "fpr": float(ae_fpr),
            "tpr": float(ae_tpr),
            "architecture": "Linear(2381->256->64->256->2381)",
            "epochs": 10,
            "lr": 0.002,
        },
    }
    metrics_path = models_dir / "evaluation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nEvaluation metrics saved to {metrics_path}")

    # Save original models for ONNX export
    with open(models_dir / "rf_model.pkl", "wb") as f:
        pickle.dump(rf, f)
    print(f"\nRandom Forest exported successfully.")

    with open(models_dir / "xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb_clf, f)
    print(f"XGBoost exported successfully.")

    with open(models_dir / "lightgbm_model.pkl", "wb") as f:
        pickle.dump(lgb_clf, f)
    print(f"LightGBM exported successfully.")

    # Also save calibrated models for pickle inference
    with open(models_dir / "rf_calibrated.pkl", "wb") as f:
        pickle.dump(rf_calibrated, f)
    with open(models_dir / "xgb_calibrated.pkl", "wb") as f:
        pickle.dump(xgb_calibrated, f)
    with open(models_dir / "lgb_calibrated.pkl", "wb") as f:
        pickle.dump(lgb_calibrated, f)
    print("Calibrated models exported successfully.")

    torch.save(ae, models_dir / "autoencoder.pt")
    print(f"PyTorch Autoencoder exported successfully.")

    # --- ONNX Export ---
    if HAS_ONNX:
        print("\n" + "=" * 50)
        print("  EXPORTING MODELS TO ONNX FORMAT")
        print("=" * 50)
        export_onnx_models(rf, xgb_clf, lgb_clf, ae, X_train_sup, models_dir)
    else:
        print("\nSkipping ONNX export (dependencies not available).")


def export_onnx_models(rf, xgb_clf, lgb_clf, ae, X_sample, models_dir):
    """Export all models to ONNX format for fast inference."""
    ndim = X_sample.shape[1]
    initial_type = [('float_input', FloatTensorType([None, ndim]))]
    
    # onnxmltools types for XGBoost/LightGBM
    try:
        from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
        onnx_initial_type = [('float_input', OnnxFloatTensorType([None, ndim]))]
    except ImportError:
        onnx_initial_type = initial_type
    
    # 1. Random Forest → ONNX
    try:
        print("  Converting Random Forest to ONNX...")
        rf_onnx = convert_sklearn(rf, initial_types=initial_type, target_opset=12)
        onnx.save(rf_onnx, models_dir / "rf_model.onnx")
        print("  [OK] rf_model.onnx saved")
    except Exception as e:
        print(f"  [FAIL] RF ONNX export failed: {e}")

    # 2. XGBoost → ONNX (via onnxmltools)
    try:
        print("  Converting XGBoost to ONNX...")
        if HAS_ONNXMLTOOLS:
            import onnxmltools
            xgb_onnx = onnxmltools.convert_xgboost(xgb_clf, initial_types=onnx_initial_type, target_opset=12)
            onnx.save(xgb_onnx, models_dir / "xgboost_model.onnx")
            print("  [OK] xgboost_model.onnx saved")
        else:
            print("  [SKIP] XGBoost ONNX export skipped (onnxmltools not available)")
    except Exception as e:
        print(f"  [FAIL] XGB ONNX export failed: {e}")

    # 3. LightGBM → ONNX (via onnxmltools)
    try:
        print("  Converting LightGBM to ONNX...")
        if HAS_ONNXMLTOOLS:
            import onnxmltools
            lgb_onnx = onnxmltools.convert_lightgbm(lgb_clf, initial_types=onnx_initial_type, target_opset=12)
            onnx.save(lgb_onnx, models_dir / "lightgbm_model.onnx")
            print("  [OK] lightgbm_model.onnx saved")
        else:
            print("  [SKIP] LightGBM ONNX export skipped (onnxmltools not available)")
    except Exception as e:
        print(f"  [FAIL] LGB ONNX export failed: {e}")

# 4. PyTorch Autoencoder → ONNX
    try:
        print("  Converting PyTorch Autoencoder to ONNX...")
        ae.eval()
        dummy_input = torch.randn(1, ndim, dtype=torch.float32)
        # Suppress verbose ONNX export output to avoid Unicode issues
        import sys
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        torch.onnx.export(
            ae,
            dummy_input,
            models_dir / "autoencoder.onnx",
            export_params=True,
            opset_version=12,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
            verbose=False
        )
        sys.stdout = old_stdout
        print("  [OK] autoencoder.onnx saved")
    except Exception as e:
        print(f"  [FAIL] AE ONNX export failed: {e}")

    print("=" * 50)


if __name__ == "__main__":
    main()
