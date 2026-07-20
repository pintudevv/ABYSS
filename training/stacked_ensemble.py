"""
Stacked Ensemble Meta-Learner
=============================
Trains a logistic regression meta-learner on the predictions of base models
(XGBoost, Random Forest, LightGBM, Autoencoder).
"""

import json
import pickle
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, precision_recall_curve, classification_report
)
import lightgbm as lgb
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier

import torch
import torch.nn as nn

# Import the base models
from train_model import Autoencoder


class StackedEnsemble:
    """Stacked ensemble with logistic regression meta-learner."""
    
    def __init__(self, meta_learner=None):
        if meta_learner is None:
            # Use calibrated logistic regression for well-calibrated probabilities
            base_lr = LogisticRegression(
                C=1.0,
                penalty='l2',
                solver='lbfgs',
                max_iter=1000,
                random_state=42,
                class_weight='balanced'
            )
            self.meta_learner = CalibratedClassifierCV(base_lr, method='isotonic', cv=3)
        else:
            self.meta_learner = meta_learner
            
        self.base_models = {}
        self.is_fitted = False
        
    def get_base_predictions(self, models_dict, X, use_onnx=False):
        """Get probability predictions from all base models."""
        predictions = {}
        
        for name, (model, is_onnx) in models_dict.items():
            if is_onnx:
                input_name = model.get_inputs()[0].name
                outputs = model.run(None, {input_name: X.astype(np.float32)})
                probs = outputs[1]  # [batch, classes]
                # Handle different output formats
                if isinstance(probs, list):
                    # RF ONNX returns list of dicts
                    n_samples = len(probs)
                    prob_array = np.zeros((n_samples, 2), dtype=np.float32)
                    for i, p in enumerate(probs):
                        for cls, prob in p.items():
                            prob_array[i, int(cls)] = prob
                    probs = prob_array
            else:
                probs = model.predict_proba(X)
            
            # Ensure we have 2 columns (binary classification)
            if probs.shape[1] == 2:
                predictions[name] = probs[:, 1]  # positive class probability
            else:
                # Multi-class - use max probability as confidence
                predictions[name] = np.max(probs, axis=1)
        
        return np.column_stack(list(predictions.values()))
    
    def fit(self, base_models_dict, X_train, y_train, X_val=None, y_val=None):
        """
        Train meta-learner on base model predictions.
        Uses cross-validation on training data to generate meta-features.
        """
        print("Generating meta-features for stacking...")
        
        # Use cross-validation to generate out-of-fold predictions for training
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        n_samples = X_train.shape[0]
        n_models = len(base_models_dict)
        
        # Meta-features: [n_samples, n_models]
        meta_X = np.zeros((n_samples, n_models))
        meta_y = y_train.copy()
        
        model_names = list(base_models_dict.keys())
        
        for fold, (train_idx, val_idx) in enumerate(cv.split(X_train, y_train)):
            print(f"  Fold {fold+1}/5...")
            X_fold_train, X_fold_val = X_train[train_idx], X_train[val_idx]
            y_fold_train = y_train[train_idx]
            
            # Retrain each base model on fold training data
            fold_models = {}
            for name, (model, is_onnx) in base_models_dict.items():
                if is_onnx:
                    fold_models[name] = (model, True)
                else:
                    # Clone and retrain
                    if 'xgb' in name.lower():
                        new_model = xgb.XGBClassifier(
                            n_estimators=100, max_depth=6, learning_rate=0.1,
                            n_jobs=-1, random_state=42
                        )
                    elif 'rf' in name.lower() or 'random' in name.lower():
                        new_model = RandomForestClassifier(
                            n_estimators=100, max_depth=15, n_jobs=-1, random_state=42
                        )
                    elif 'lgb' in name.lower() or 'light' in name.lower():
                        new_model = lgb.LGBMClassifier(
                            n_estimators=100, max_depth=6, learning_rate=0.1,
                            num_leaves=63, n_jobs=-1, random_state=42, verbosity=-1
                        )
                    else:
                        new_model = model.__class__(**model.get_params())
                    
                    new_model.fit(X_fold_train, y_fold_train)
                    fold_models[name] = (new_model, False)
            
            # Generate predictions on validation fold
            meta_X_val = self.get_base_predictions(fold_models, X_fold_val)
            meta_X[val_idx] = meta_X_val
        
        # Train meta-learner on full meta-features
        print("Training meta-learner...")
        self.meta_learner.fit(meta_X, meta_y)
        self.base_model_names = model_names
        self.is_fitted = True
        
        # Also train on full training set for final base models
        self.base_models = {}
        for name, (model, is_onnx) in base_models_dict.items():
            self.base_models[name] = (model, is_onnx)
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            val_meta_X = self.get_base_predictions(self.base_models, X_val)
            val_preds = self.meta_learner.predict(val_meta_X)
            val_probs = self.meta_learner.predict_proba(val_meta_X)[:, 1]
            
            print("\nStacked Ensemble Validation Metrics:")
            print(f"  Accuracy: {accuracy_score(y_val, val_preds):.4f}")
            print(f"  Precision: {precision_score(y_val, val_preds, zero_division=0):.4f}")
            print(f"  Recall: {recall_score(y_val, val_preds, zero_division=0):.4f}")
            print(f"  F1: {f1_score(y_val, val_preds, zero_division=0):.4f}")
            print(f"  ROC-AUC: {roc_auc_score(y_val, val_probs):.4f}")
            
            # PR-AUC
            precision, recall, _ = precision_recall_curve(y_val, val_probs)
            pr_auc = np.trapz(precision, recall)
            print(f"  PR-AUC: {pr_auc:.4f}")
    
    def predict_proba(self, X):
        """Get calibrated probability predictions from stacked ensemble."""
        if not self.is_fitted:
            raise ValueError("Ensemble not fitted. Call fit() first.")
        
        meta_X = self.get_base_predictions(self.base_models, X)
        return self.meta_learner.predict_proba(meta_X)
    
    def predict(self, X):
        """Get class predictions from stacked ensemble."""
        if not self.is_fitted:
            raise ValueError("Ensemble not fitted. Call fit() first.")
        
        meta_X = self.get_base_predictions(self.base_models, X)
        return self.meta_learner.predict(meta_X)
    
    def save(self, path):
        """Save the stacked ensemble."""
        with open(path, 'wb') as f:
            pickle.dump({
                'meta_learner': self.meta_learner,
                'base_model_names': self.base_model_names,
                'is_fitted': self.is_fitted,
            }, f)
        print(f"Stacked ensemble saved to {path}")
    
    @classmethod
    def load(cls, path):
        """Load the stacked ensemble."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        ensemble = cls()
        ensemble.meta_learner = data['meta_learner']
        ensemble.base_model_names = data['base_model_names']
        ensemble.is_fitted = data['is_fitted']
        return ensemble


def evaluate_stacked_ensemble(ensemble, X_test, y_test, base_models_dict):
    """Comprehensive evaluation of stacked ensemble vs individual models."""
    print("=" * 60)
    print("  STACKED ENSEMBLE EVALUATION")
    print("=" * 60)
    
    # Get meta-features
    meta_X = ensemble.get_base_predictions(base_models_dict, X_test)
    
    # Individual model evaluations
    print("\n--- Individual Model Performance ---")
    for i, name in enumerate(ensemble.base_model_names):
        model_probs = meta_X[:, i]
        model_preds = (model_probs > 0.5).astype(int)
        
        acc = accuracy_score(y_test, model_preds)
        f1 = f1_score(y_test, model_preds, zero_division=0)
        auc = roc_auc_score(y_test, model_probs)
        
        print(f"  {name:15s} | Acc: {acc:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")
    
    # Stacked ensemble
    stacked_probs = ensemble.predict_proba(X_test)[:, 1]
    stacked_preds = ensemble.predict(X_test)
    
    acc = accuracy_score(y_test, stacked_preds)
    f1 = f1_score(y_test, stacked_preds, zero_division=0)
    auc = roc_auc_score(y_test, stacked_probs)
    
    print(f"\n  {'Stacked':15s} | Acc: {acc:.4f} | F1: {f1:.4f} | AUC: {auc:.4f}")
    
    # Weighted average ensemble (for comparison)
    avg_probs = np.mean(meta_X, axis=1)
    avg_preds = (avg_probs > 0.5).astype(int)
    avg_acc = accuracy_score(y_test, avg_preds)
    avg_f1 = f1_score(y_test, avg_preds, zero_division=0)
    avg_auc = roc_auc_score(y_test, avg_probs)
    print(f"  {'Avg Ensemble':15s} | Acc: {avg_acc:.4f} | F1: {avg_f1:.4f} | AUC: {avg_auc:.4f}")
    
    return {
        'stacked': {'accuracy': acc, 'f1': f1, 'auc': auc},
        'average': {'accuracy': avg_acc, 'f1': avg_f1, 'auc': avg_auc},
    }


if __name__ == "__main__":
    # Full training on EMBER data
    import torch
    from train_model import Autoencoder
    import joblib
    
    # Load data
    ndim = 2381
    y_test = np.memmap("ember2018/y_test.dat", dtype=np.float32, mode="r")
    n_test = y_test.shape[0]
    X_test = np.memmap("ember2018/X_test.dat", dtype=np.float32, mode="r", shape=(n_test, ndim))
    y_test = np.memmap("ember2018/y_test.dat", dtype=np.float32, mode="r", shape=(n_test,))
    
    test_labeled_mask = (y_test >= 0)
    X_test = X_test[test_labeled_mask]
    y_test = y_test[test_labeled_mask].astype(np.int32)
    
    # Also load train data for stacking
    y_train = np.memmap("ember2018/y_train.dat", dtype=np.float32, mode="r")
    n_train = y_train.shape[0]
    X_train = np.memmap("ember2018/X_train.dat", dtype=np.float32, mode="r", shape=(n_train, ndim))
    y_train = np.memmap("ember2018/y_train.dat", dtype=np.float32, mode="r", shape=(n_train,))
    
    train_labeled_mask = (y_train >= 0)
    X_train = X_train[train_labeled_mask]
    y_train = y_train[train_labeled_mask].astype(np.int32)
    
    print(f"Train: {X_train.shape}, Test: {X_test.shape}")
    
    # Load models
    models_dir = Path("../backend/models")
    
    with open(models_dir / "rf_model.pkl", "rb") as f:
        rf = pickle.load(f)
    with open(models_dir / "xgboost_model.pkl", "rb") as f:
        xgb_model = pickle.load(f)
    with open(models_dir / "lightgbm_model.pkl", "rb") as f:
        lgb_model = pickle.load(f)
    
    # Load autoencoder
    ae = torch.load(models_dir / "autoencoder.pt", map_location="cpu", weights_only=False)
    ae.eval()
    
    # Load scaler for AE
    ae_scaler = joblib.load(models_dir / "ae_scaler.pkl")
    
    # Wrap AE to provide predict_proba
    class AEWrapper:
        def __init__(self, ae, scaler):
            self.ae = ae
            self.scaler = scaler
        
        def get_params(self, deep=True):
            return {'ae': self.ae, 'scaler': self.scaler}
        
        def set_params(self, **params):
            for k, v in params.items():
                setattr(self, k, v)
            return self
        
        def fit(self, X, y=None):
            # Pre-trained, no fitting needed
            return self
        
        def predict_proba(self, X):
            X_scaled = self.scaler.transform(X)
            self.ae.eval()
            with torch.no_grad():
                X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
                recon = self.ae(X_tensor)
                errors = torch.mean((X_tensor - recon) ** 2, dim=1).numpy()
            threshold = 4.5
            probs = np.zeros((len(errors), 2))
            probs[:, 1] = np.clip(errors / (threshold * 10), 0, 1)
            probs[:, 0] = 1 - probs[:, 1]
            return probs
    
    ae_wrapper = AEWrapper(ae, ae_scaler)
    
    base_models = {
        'rf': (rf, False),
        'xgb': (xgb_model, False),
        'lgbm': (lgb_model, False),
        'ae': (ae_wrapper, False),
    }
    
    # Train stacked ensemble
    ensemble = StackedEnsemble()
    ensemble.fit(base_models, X_train, y_train, X_test, y_test)
    
    # Save ensemble
    ensemble.save(models_dir / "stacked_ensemble.pkl")
    
    print("\nStacked ensemble training completed!")