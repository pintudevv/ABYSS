"""
StealthOS — Real EMBER Model Training Script (Step 2)
=====================================================
Trains supervised models (RF, XGBoost) and unsupervised anomaly model (PyTorch Autoencoder)
using the real vectorized EMBER 2018 dataset (2381 features).
Saves trained binaries to backend/models/ directory.
"""

from __future__ import annotations

import os
import pickle
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import xgboost as xgb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

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

    # 4. Train PyTorch Autoencoder (trained only on Benign class 0)
    print("\nTraining PyTorch Autoencoder on Benign EMBER data...")
    X_train_clean = X_train[y_train == 0]
    
    # Custom Autoencoder definition with 2381 inputs
    train_dataset = TensorDataset(torch.tensor(X_train_clean, dtype=torch.float32))
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)

    ae = Autoencoder()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(ae.parameters(), lr=0.002)

    ae.train()
    for epoch in range(10):
        epoch_loss = 0.0
        for batch in train_loader:
            x_batch = batch[0]
            optimizer.zero_grad()
            outputs = ae(x_batch)
            loss = criterion(outputs, x_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * x_batch.size(0)
        print(f"  Epoch {epoch+1:2d}/10 | MSE Loss: {epoch_loss / len(X_train_clean):.6f}")

    # Evaluate Autoencoder on Test Set (FPR / TPR)
    ae.eval()
    with torch.no_grad():
        X_test_clean = X_test_sup[y_test_sup == 0]
        X_test_mal = X_test_sup[y_test_sup == 1]
        
        clean_tensors = torch.tensor(X_test_clean, dtype=torch.float32)
        mal_tensors = torch.tensor(X_test_mal, dtype=torch.float32)
        
        clean_errors = torch.mean((clean_tensors - ae(clean_tensors))**2, dim=1).numpy()
        mal_errors = torch.mean((mal_tensors - ae(mal_tensors))**2, dim=1).numpy()

    threshold = np.percentile(clean_errors, 95)
    ae_fpr = np.mean(clean_errors > threshold)
    ae_tpr = np.mean(mal_errors > threshold)

    print("\n" + "=" * 50)
    print("  AUTOENCODER ANOMALY DETECTION EVALUATION")
    print("=" * 50)
    print(f"  Anomaly Threshold (95th % clean): {threshold:.6f}")
    print(f"  False Positive Rate (FPR)       : {ae_fpr * 100:.2f}%")
    print(f"  True Positive Rate (TPR)        : {ae_tpr * 100:.2f}%")
    print("=" * 50)

    # Save models, overwriting the synthetic ones
    with open(models_dir / "rf_model.pkl", "wb") as f:
        pickle.dump(rf, f)
    print(f"\nRandom Forest exported successfully.")

    with open(models_dir / "xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb_clf, f)
    print(f"XGBoost exported successfully.")

    torch.save(ae, models_dir / "autoencoder.pt")
    print(f"PyTorch Autoencoder exported successfully.")

if __name__ == "__main__":
    main()
