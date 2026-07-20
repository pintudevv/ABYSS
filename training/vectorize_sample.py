"""
ABYSS — Real EMBER Vectorizer
=================================
Monkey-patches sklearn FeatureHasher to avoid ValueError in newer scikit-learn.
Extracts a balanced subset of EMBER2018 (2381-dimensional features) from the JSONL files.
Saves X_train.dat, y_train.dat, X_test.dat, y_test.dat in the ember2018 directory.

Usage:
    python vectorize_sample.py [--train-samples N] [--test-samples M]
"""

import os
import json
import argparse
import numpy as np
import sklearn.feature_extraction
from pathlib import Path
from tqdm import tqdm

# --- 1. Scikit-Learn compatibility monkey-patch ---
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

# --- 2. Try importing ember ---
try:
    import ember
    HAS_EMBER = True
except ImportError:
    HAS_EMBER = False
    print("WARNING: ember not installed. Install with: pip install ember")


def vectorize_dataset(source_path: Path, output_X: Path, output_y: Path, max_samples: int, extractor) -> int:
    """Vectorize a JSONL dataset to memmap arrays."""
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    dim = extractor.dim
    print(f"  Reading {source_path.name} (max {max_samples} samples, {dim} features)...")
    
    X_memmap = np.memmap(output_X, dtype=np.float32, mode="w+", shape=(max_samples, dim))
    y_memmap = np.memmap(output_y, dtype=np.float32, mode="w+", shape=(max_samples,))
    
    actual_count = 0
    with open(source_path, "r", encoding="utf-8") as f:
        for idx in tqdm(range(max_samples), desc=f"  Vectorizing {source_path.name}"):
            line = f.readline()
            if not line:
                break
            try:
                data = json.loads(line)
                X_memmap[idx] = extractor.process_raw_features(data)
                y_memmap[idx] = data.get("label", -1)
                actual_count += 1
            except Exception as e:
                print(f"  Warning: Failed to process line {idx}: {e}")
                continue
    
    # Trim to actual count if fewer samples
    if actual_count < max_samples:
        X_memmap = X_memmap[:actual_count]
        y_memmap = y_memmap[:actual_count]
    
    X_memmap.flush()
    y_memmap.flush()
    print(f"  Done: {actual_count} samples written")
    return actual_count


def main():
    parser = argparse.ArgumentParser(description="Vectorize EMBER 2018 dataset")
    parser.add_argument("--train-samples", type=int, default=60000, help="Max training samples (default: 60000)")
    parser.add_argument("--test-samples", type=int, default=3000, help="Max test samples (default: 3000)")
    parser.add_argument("--data-dir", type=Path, default=Path("ember2018"), help="Directory with JSONL files")
    args = parser.parse_args()

    if not HAS_EMBER:
        print("ERROR: ember package required. Install with: pip install ember")
        return 1

    base_dir = Path(args.data_dir)
    ext = ember.PEFeatureExtractor(2)
    dim = ext.dim
    print(f"PEFeatureExtractor v2 dimension: {dim}")

    # Define file paths
    train_sources = [
        base_dir / "train_features_0.jsonl",
        base_dir / "train_features_1.jsonl",
        base_dir / "train_features_2.jsonl",
        base_dir / "train_features_3.jsonl",
        base_dir / "train_features_4.jsonl",
        base_dir / "train_features_5.jsonl",
    ]
    test_source = base_dir / "test_features.jsonl"

    output_dir = base_dir
    output_dir.mkdir(exist_ok=True)

    # --- Vectorize training data (combine all train files) ---
    train_X_path = output_dir / "X_train.dat"
    train_y_path = output_dir / "y_train.dat"
    
    total_train = 0
    samples_per_file = max(1, args.train_samples // len(train_sources))
    
    for src in train_sources:
        if total_train >= args.train_samples:
            break
        remaining = args.train_samples - total_train
        count = min(samples_per_file, remaining)
        
        # Create temporary output for this chunk
        chunk_X = output_dir / f"X_train_chunk_{src.stem}.dat"
        chunk_y = output_dir / f"y_train_chunk_{src.stem}.dat"
        
        n = vectorize_dataset(src, chunk_X, chunk_y, count, ext)
        total_train += n

    # Concatenate all train chunks
    if total_train > 0:
        print(f"Concatenating {total_train} training samples...")
        all_X = np.memmap(train_X_path, dtype=np.float32, mode="w+", shape=(total_train, dim))
        all_y = np.memmap(train_y_path, dtype=np.float32, mode="w+", shape=(total_train,))
        
        offset = 0
        for src in train_sources:
            chunk_X = output_dir / f"X_train_chunk_{src.stem}.dat"
            chunk_y = output_dir / f"y_train_chunk_{src.stem}.dat"
            if chunk_X.exists():
                chunk_data_X = np.memmap(chunk_X, dtype=np.float32, mode="r", shape=(-1, dim))
                chunk_data_y = np.memmap(chunk_y, dtype=np.float32, mode="r", shape=(-1,))
                n_chunk = chunk_data_X.shape[0]
                all_X[offset:offset+n_chunk] = chunk_data_X
                all_y[offset:offset+n_chunk] = chunk_data_y
                offset += n_chunk
                # Clean up chunk
                chunk_X.unlink(missing_ok=True)
                chunk_y.unlink(missing_ok=True)
        
        all_X.flush()
        all_y.flush()
        print(f"Training data saved: X_train.dat ({total_train}, {dim}), y_train.dat ({total_train})")

    # --- Vectorize test data ---
    test_X_path = output_dir / "X_test.dat"
    test_y_path = output_dir / "y_test.dat"
    
    n_test = vectorize_dataset(test_source, test_X_path, test_y_path, args.test_samples, ext)
    print(f"Test data saved: X_test.dat ({n_test}, {dim}), y_test.dat ({n_test})")

    print("\nDone! You can now run train_model.py")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())