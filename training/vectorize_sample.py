"""
StealthOS — Real EMBER Vectorizer
==================================
Monkey-patches sklearn FeatureHasher to avoid ValueError in newer scikit-learn.
Extracts a real, balanced subset of EMBER2018 (2381-dimensional features) from the JSONL files.
Saves X_train.dat, y_train.dat, X_test.dat, y_test.dat in the ember2018 directory.
"""

import os
import json
import numpy as np
import sklearn.feature_extraction
from pathlib import Path
from tqdm import tqdm
import ember

# 1. Apply Scikit-Learn compatibility monkey-patch
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

def main():
    base_dir = Path("ember2018")
    ext = ember.PEFeatureExtractor(2)
    dim = ext.dim
    print(f"PEFeatureExtractor version 2 dimension: {dim}")

    # Vectorize Train Set
    train_source = base_dir / "train_features_1.jsonl"
    train_count = 15000
    X_train_path = base_dir / "X_train.dat"
    y_train_path = base_dir / "y_train.dat"

    print(f"Creating X_train.dat and y_train.dat ({train_count} samples from {train_source.name})...")
    X_train = np.memmap(X_train_path, dtype=np.float32, mode="w+", shape=(train_count, dim))
    y_train = np.memmap(y_train_path, dtype=np.float32, mode="w+", shape=train_count)

    with open(train_source, "r", encoding="utf-8") as f:
        for idx in tqdm(range(train_count)):
            line = f.readline()
            if not line:
                break
            data = json.loads(line)
            X_train[idx] = ext.process_raw_features(data)
            y_train[idx] = data.get("label", -1)

    X_train.flush()
    y_train.flush()
    print("Train features successfully vectorized.")

    # Vectorize Test Set
    test_source = base_dir / "test_features.jsonl"
    test_count = 3000
    X_test_path = base_dir / "X_test.dat"
    y_test_path = base_dir / "y_test.dat"

    print(f"Creating X_test.dat and y_test.dat ({test_count} samples from {test_source.name})...")
    X_test = np.memmap(X_test_path, dtype=np.float32, mode="w+", shape=(test_count, dim))
    y_test = np.memmap(y_test_path, dtype=np.float32, mode="w+", shape=test_count)

    with open(test_source, "r", encoding="utf-8") as f:
        for idx in tqdm(range(test_count)):
            line = f.readline()
            if not line:
                break
            data = json.loads(line)
            X_test[idx] = ext.process_raw_features(data)
            y_test[idx] = data.get("label", -1)

    X_test.flush()
    y_test.flush()
    print("Test features successfully vectorized.")

if __name__ == "__main__":
    main()
