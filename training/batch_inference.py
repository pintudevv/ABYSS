"""
Batch Inference + ONNX INT8 Quantization for ABYSS
===================================================
Provides:
- Batch inference pipeline for multiple files
- ONNX INT8 quantization for faster inference
- Benchmarking utilities
"""

import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType
from pathlib import Path
import time
from typing import List, Dict, Tuple
import pickle


class BatchInferenceEngine:
    """Optimized batch inference for multiple models."""
    
    def __init__(self, models_dir: Path, use_onnx: bool = True):
        self.models_dir = Path(models_dir)
        self.use_onnx = use_onnx
        self.sessions = {}
        self.scalers = {}
        
    def load_models(self):
        """Load all ONNX models and scalers."""
        model_files = {
            'rf': 'rf_model.onnx',
            'xgb': 'xgboost_model.onnx',
            'lgbm': 'lightgbm_model.onnx',
            'ae': 'autoencoder.onnx',
        }
        
        for name, fname in model_files.items():
            path = self.models_dir / fname
            if path.exists():
                sess = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
                self.sessions[name] = sess
                print(f"Loaded ONNX: {name}")
        
        # Load scalers
        ae_scaler_path = self.models_dir / "ae_scaler.pkl"
        if ae_scaler_path.exists():
            import joblib
            self.scalers['ae'] = joblib.load(ae_scaler_path)
    
    def predict_batch(self, features: np.ndarray, batch_size: int = 32) -> Dict[str, np.ndarray]:
        """
        Run inference on batch of features.
        
        Args:
            features: (n_samples, 2381) feature matrix
            batch_size: Batch size for processing
            
        Returns:
            Dict of model_name -> probabilities (n_samples, 2)
        """
        n_samples = features.shape[0]
        results = {}
        
        for name, session in self.sessions.items():
            probs = np.zeros((n_samples, 2), dtype=np.float32)
            
            for i in range(0, n_samples, batch_size):
                batch = features[i:i+batch_size].astype(np.float32)
                
                # Apply scaler for autoencoder
                if name == 'ae' and 'ae' in self.scalers:
                    batch = self.scalers['ae'].transform(batch)
                
                input_name = session.get_inputs()[0].name
                outputs = session.run(None, {input_name: batch})
                
                if name in ['rf', 'xgb', 'lgbm']:
                    # Handle different output formats
                    if isinstance(outputs[1], list):
                        # RF returns list of dicts
                        batch_probs = np.zeros((len(batch), 2), dtype=np.float32)
                        for j, prob_dict in enumerate(outputs[1]):
                            for cls, prob in prob_dict.items():
                                batch_probs[j, int(cls)] = prob
                    else:
                        batch_probs = outputs[1]
                    probs[i:i+batch_size] = batch_probs
                else:
                    # Autoencoder returns reconstruction
                    pass
            
            results[name] = probs
        
        return results


def quantize_onnx_models(
    models_dir: Path,
    output_dir: Path,
    quant_type: QuantType = QuantType.QInt8,
    per_channel: bool = True,
    reduce_range: bool = True,
) -> Dict[str, Dict]:
    """
    Quantize ONNX models to INT8 for faster inference.
    
    Args:
        models_dir: Directory containing FP32 ONNX models
        output_dir: Directory for quantized models
        quant_type: Quantization type (QInt8 or QUInt8)
        per_channel: Use per-channel quantization
        reduce_range: Reduce range for activation quantization
        
    Returns:
        Dict with quantization results and size comparison
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_files = {
        'rf': 'rf_model.onnx',
        'xgb': 'xgboost_model.onnx',
        'lgbm': 'lightgbm_model.onnx',
        'ae': 'autoencoder.onnx',
    }
    
    results = {}
    
    for name, fname in model_files.items():
        input_path = models_dir / fname
        output_path = output_dir / f"{name}_int8.onnx"
        
        if not input_path.exists():
            print(f"Skipping {name}: {input_path} not found")
            continue
        
        print(f"Quantizing {name}...")
        
        # Get original size
        orig_size = input_path.stat().st_size / 1024 / 1024
        
        try:
            quantize_dynamic(
                model_input=str(input_path),
                model_output=str(output_path),
                op_types_to_quantize=['MatMul', 'Gemm', 'Conv', 'Add'],
                weight_type=quant_type,
                per_channel=per_channel,
                reduce_range=reduce_range,
            )
            
            # Verify quantized model
            quant_model = onnx.load(str(output_path))
            onnx.checker.check_model(quant_model)
            
            quant_size = output_path.stat().st_size / 1024 / 1024
            reduction = (1 - quant_size / orig_size) * 100
            
            results[name] = {
                'original_size_mb': orig_size,
                'quantized_size_mb': quant_size,
                'reduction_percent': reduction,
                'status': 'success',
            }
            print(f"  {name}: {orig_size:.1f}MB -> {quant_size:.1f}MB ({reduction:.1f}% reduction)")
            
        except Exception as e:
            results[name] = {'status': 'failed', 'error': str(e)}
            print(f"  {name}: FAILED - {e}")
    
    return results


def benchmark_inference(
    models_dir: Path,
    test_features: np.ndarray,
    batch_sizes: List[int] = [1, 8, 16, 32, 64, 128],
    num_runs: int = 10,
) -> Dict:
    """
    Benchmark inference latency at different batch sizes.
    
    Args:
        models_dir: Directory with ONNX models
        test_features: Test feature matrix (n_samples, 2381)
        batch_sizes: List of batch sizes to test
        num_runs: Number of runs to average
        
    Returns:
        Dict with latency results per model per batch size
    """
    engine = BatchInferenceEngine(models_dir)
    engine.load_models()
    
    results = {}
    
    for name, session in engine.sessions.items():
        results[name] = {}
        
        for batch_size in batch_sizes:
            latencies = []
            
            for _ in range(num_runs):
                # Create batch
                if len(test_features) >= batch_size:
                    batch = test_features[:batch_size]
                else:
                    # Repeat features to fill batch
                    repeats = (batch_size // len(test_features)) + 1
                    batch = np.tile(test_features, (repeats, 1))[:batch_size]
                
                batch = batch.astype(np.float32)
                input_name = session.get_inputs()[0].name
                
                # Warmup
                session.run(None, {input_name: batch})
                
                # Timed runs
                start = time.perf_counter()
                session.run(None, {input_name: batch})
                elapsed = (time.perf_counter() - start) * 1000  # ms
                latencies.append(elapsed)
            
            results[name][batch_size] = {
                'mean_ms': np.mean(latencies),
                'std_ms': np.std(latencies),
                'p50_ms': np.percentile(latencies, 50),
                'p95_ms': np.percentile(latencies, 95),
                'p99_ms': np.percentile(latencies, 99),
            }
            print(f"  {name} batch={batch_size}: {np.mean(latencies):.2f}ms ± {np.std(latencies):.2f}ms")
    
    return results


def compare_fp32_int8(
    models_dir: Path,
    int8_dir: Path,
    test_features: np.ndarray,
) -> Dict:
    """Compare FP32 vs INT8 model accuracy and speed."""
    results = {}
    
    for name in ['rf', 'xgb', 'lgbm', 'ae']:
        fp32_path = models_dir / f"{name}_model.onnx" if name != 'ae' else models_dir / "autoencoder.onnx"
        int8_path = int8_dir / f"{name}_int8.onnx"
        
        if not fp32_path.exists() or not int8_path.exists():
            continue
        
        fp32_sess = ort.InferenceSession(str(fp32_path), providers=['CPUExecutionProvider'])
        int8_sess = ort.InferenceSession(str(int8_path), providers=['CPUExecutionProvider'])
        
        input_name = fp32_sess.get_inputs()[0].name
        
        # Compare outputs on test data
        batch = test_features[:100].astype(np.float32)
        
        fp32_out = fp32_sess.run(None, {input_name: batch})
        int8_out = int8_sess.run(None, {input_name: batch})
        
        # Compare predictions
        if name in ['rf', 'xgb', 'lgbm']:
            if isinstance(fp32_out[1], list):
                # Convert dict list to array
                fp32_probs = np.zeros((len(batch), 2))
                int8_probs = np.zeros((len(batch), 2))
                for i, (fp32_dict, int8_dict) in enumerate(zip(fp32_out[1], int8_out[1])):
                    for cls, prob in fp32_dict.items():
                        fp32_probs[i, int(cls)] = prob
                    for cls, prob in int8_dict.items():
                        int8_probs[i, int(cls)] = prob
            else:
                fp32_probs = fp32_out[1]
                int8_probs = int8_out[1]
            
            fp32_preds = fp32_probs.argmax(axis=1)
            int8_preds = int8_probs.argmax(axis=1)
            
            agreement = np.mean(fp32_preds == int8_preds)
            prob_diff = np.mean(np.abs(fp32_probs - int8_probs))
            
            results[name] = {
                'prediction_agreement': agreement,
                'mean_prob_diff': prob_diff,
                'fp32_preds': fp32_preds,
                'int8_preds': int8_preds,
            }
            print(f"  {name}: Agreement={agreement:.4f}, MeanProbDiff={prob_diff:.6f}")
    
    return results


if __name__ == "__main__":
    import time
    
    models_dir = Path("../backend/models")
    int8_dir = Path("../backend/models_int8")
    
    # Load test features
    test_dir = Path("ember2018")
    ndim = 2381
    y_test = np.memmap(test_dir / "y_test.dat", dtype=np.float32, mode="r")
    n_test = y_test.shape[0]
    X_test = np.memmap(test_dir / "X_test.dat", dtype=np.float32, mode="r", shape=(n_test, ndim))
    
    test_labeled = (y_test >= 0)
    X_test = X_test[test_labeled]
    
    print("=== ONNX INT8 Quantization ===")
    quant_results = quantize_onnx_models(models_dir, int8_dir)
    
    print("\n=== FP32 vs INT8 Comparison ===")
    compare_fp32_int8(models_dir, int8_dir, X_test)
    
    print("\n=== Latency Benchmark ===")
    benchmark_results = benchmark_inference(models_dir, X_test[:1000])
    
    # Save results
    import json
    with open(int8_dir / "benchmark_results.json", "w") as f:
        json.dump({
            'quantization': quant_results,
            'benchmark': benchmark_results,
        }, f, indent=2)
    print(f"\nResults saved to {int8_dir / 'benchmark_results.json'}")