"""
StealthOS — Custom Suspicious PE Test Runner
============================================
Runs the static analysis and classification pipeline on the custom compiled
suspicious binary (test_suspicious.exe) to verify ML model prediction capabilities.
"""

import subprocess
from pathlib import Path
import json

def main():
    base_dir = Path(__file__).parent
    backend_dir = base_dir.parent / "backend"
    results_dir = backend_dir / "results"
    results_dir.mkdir(exist_ok=True)

    malware_exe = base_dir / "test_suspicious.exe"
    if not malware_exe.exists():
        print(f"Target binary missing: {malware_exe}")
        return

    # 1. Run Static Analysis
    print("Running static analysis on test_suspicious.exe...")
    features_dir = results_dir / "custom_features_dir"
    features_json = features_dir / "features.json"
    static_script = backend_dir / "static_analysis.py"
    
    try:
        import os
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        subprocess.run([
            "python", str(static_script),
            str(malware_exe),
            "--output", str(features_dir)
        ], env=env, check=True)
        print(f"Static features saved to {features_json}")
    except subprocess.CalledProcessError as e:
        print(f"Static analysis failed: {e}")
        return

    # 2. Run Classifier
    print("Running ML Classifier on custom features...")
    classifier_script = backend_dir / "classifier.py"
    try:
        subprocess.run([
            "python", str(classifier_script),
            "--features", str(features_json)
        ], env=env, check=True)
        print("Classification complete!")
    except subprocess.CalledProcessError as e:
        print(f"Classification failed: {e}")
        return

if __name__ == "__main__":
    main()
