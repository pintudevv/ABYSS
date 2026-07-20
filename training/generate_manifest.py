#!/usr/bin/env python3
"""
Generate model manifest with SHA256 hashes for integrity verification.
Run after training to create model_manifest.json in backend/models/
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime

MODELS_DIR = Path(__file__).parent.parent / "backend" / "models"
MANIFEST_PATH = MODELS_DIR / "model_manifest.json"

MODEL_FILES = [
    "rf_model.pkl",
    "xgboost_model.pkl", 
    "autoencoder.pt",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "models": {}
    }
    
    for fname in MODEL_FILES:
        fpath = MODELS_DIR / fname
        if fpath.exists():
            digest = sha256_file(fpath)
            size = fpath.stat().st_size
            manifest["models"][fname] = {
                "sha256": digest,
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 2)
            }
            print(f"  {fname}: {digest[:16]}... ({size/1024/1024:.1f} MB)")
        else:
            print(f"  {fname}: NOT FOUND")
    
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nManifest saved to {MANIFEST_PATH}")
    return 0

if __name__ == "__main__":
    exit(main())