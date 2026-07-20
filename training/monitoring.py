"""
Monitoring System for ABYSS ML Pipeline
=========================================
Provides:
- Prediction latency tracking (p50, p95, p99)
- Confidence score distributions
- Data drift detection (population stability index, KL divergence)
- Model performance monitoring
- Alerting thresholds
"""

import json
import time
import numpy as np
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import warnings

try:
    from scipy import stats
    from scipy.spatial.distance import jensenshannon
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    warnings.warn("scipy not installed - drift detection limited")


@dataclass
class PredictionMetrics:
    """Metrics for a single prediction."""
    timestamp: float
    latency_ms: float
    model_name: str
    prediction: int
    confidence: float
    threat_type: str
    features_hash: str  # For drift detection


@dataclass
class LatencyStats:
    """Latency statistics."""
    count: int
    mean_ms: float
    std_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float


@dataclass
class DriftMetrics:
    """Data drift metrics."""
    timestamp: float
    psi_score: float  # Population Stability Index
    kl_divergence: float
    feature_drifts: Dict[str, float]  # Per-feature drift
    alert: bool


class LatencyTracker:
    """Thread-safe latency tracking with percentile computation."""
    
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._lock = threading.Lock()
        self._latencies = deque(maxlen=max_samples)
        self._model_latencies = {}  # model_name -> deque
    
    def record(self, model_name: str, latency_ms: float):
        with self._lock:
            self._latencies.append(latency_ms)
            if model_name not in self._model_latencies:
                self._model_latencies[model_name] = deque(maxlen=self.max_samples)
            self._model_latencies[model_name].append(latency_ms)
    
    def get_stats(self, model_name: Optional[str] = None) -> LatencyStats:
        with self._lock:
            if model_name and model_name in self._model_latencies:
                data = np.array(self._model_latencies[model_name])
            else:
                data = np.array(self._latencies)
            
            if len(data) == 0:
                return LatencyStats(0, 0, 0, 0, 0, 0, 0, 0)
            
            return LatencyStats(
                count=len(data),
                mean_ms=float(np.mean(data)),
                std_ms=float(np.std(data)),
                p50_ms=float(np.percentile(data, 50)),
                p95_ms=float(np.percentile(data, 95)),
                p99_ms=float(np.percentile(data, 99)),
                min_ms=float(np.min(data)),
                max_ms=float(np.max(data)),
            )
    
    def get_all_model_stats(self) -> Dict[str, LatencyStats]:
        with self._lock:
            return {name: self.get_stats(name) for name in self._model_latencies}


class ConfidenceTracker:
    """Track confidence score distributions and detect anomalies."""
    
    def __init__(self, max_samples: int = 10000, bins: int = 50):
        self.max_samples = max_samples
        self.bins = bins
        self._lock = threading.Lock()
        self._confidences = deque(maxlen=max_samples)
        self._confidence_by_class = {0: deque(maxlen=max_samples), 1: deque(maxlen=max_samples)}
        self._confidence_by_model = {}
        self._hist_bins = np.linspace(0, 1, bins + 1)
    
    def record(self, confidence: float, prediction: int, model_name: str):
        with self._lock:
            self._confidences.append(confidence)
            self._confidence_by_class[prediction].append(confidence)
            
            if model_name not in self._confidence_by_model:
                self._confidence_by_model[model_name] = deque(maxlen=self.max_samples)
            self._confidence_by_model[model_name].append(confidence)
    
    def get_distribution(self, model_name: Optional[str] = None) -> Dict:
        with self._lock:
            if model_name and model_name in self._confidence_by_model:
                data = np.array(self._confidence_by_model[model_name])
            else:
                data = np.array(self._confidences)
            
            if len(data) == 0:
                return {}
            
            hist, bin_edges = np.histogram(data, bins=self._hist_bins, density=True)
            
            return {
                'count': len(data),
                'mean': float(np.mean(data)),
                'std': float(np.std(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'percentiles': {
                    'p10': float(np.percentile(data, 10)),
                    'p25': float(np.percentile(data, 25)),
                    'p50': float(np.percentile(data, 50)),
                    'p75': float(np.percentile(data, 75)),
                    'p90': float(np.percentile(data, 90)),
                    'p95': float(np.percentile(data, 95)),
                    'p99': float(np.percentile(data, 99)),
                },
                'histogram': {
                    'bins': bin_edges.tolist(),
                    'counts': hist.tolist(),
                },
                'low_confidence_rate': float(np.mean(data < 0.5)),
                'high_confidence_rate': float(np.mean(data > 0.9)),
            }
    
    def get_class_conditional_distribution(self) -> Dict[int, Dict]:
        """Get confidence distribution per prediction class."""
        with self._lock:
            result = {}
            for cls in [0, 1]:
                data = np.array(self._confidence_by_class[cls])
                if len(data) > 0:
                    result[cls] = {
                        'count': len(data),
                        'mean': float(np.mean(data)),
                        'std': float(np.std(data)),
                    }
            return result


class DriftDetector:
    """
    Detect data drift using Population Stability Index (PSI) and KL divergence.
    
    PSI = sum((actual% - expected%) * log(actual% / expected%))
    PSI < 0.1: No significant drift
    PSI 0.1-0.25: Moderate drift
    PSI > 0.25: Significant drift
    """
    
    def __init__(
        self,
        reference_features: np.ndarray,
        feature_names: List[str],
        n_bins: int = 10,
        psi_threshold: float = 0.1,
    ):
        """
        Args:
            reference_features: Reference (training) feature matrix (n_samples, n_features)
            feature_names: Names of features
            n_bins: Number of bins for histogram
            psi_threshold: PSI threshold for alert
        """
        self.feature_names = feature_names
        self.n_bins = n_bins
        self.psi_threshold = psi_threshold
        self._lock = threading.Lock()
        
        # Compute reference distributions
        self.reference_distributions = {}
        self.bin_edges = {}
        
        for i, name in enumerate(feature_names):
            feat_data = reference_features[:, i]
            # Use quantile-based bins for better distribution
            bin_edges = np.percentile(feat_data, np.linspace(0, 100, n_bins + 1))
            # Ensure unique edges
            bin_edges = np.unique(bin_edges)
            if len(bin_edges) < 2:
                bin_edges = np.array([np.min(feat_data), np.max(feat_data)])
            
            hist, _ = np.histogram(feat_data, bins=bin_edges, density=True)
            # Add small epsilon to avoid division by zero
            hist = hist + 1e-10
            hist = hist / hist.sum()
            
            self.reference_distributions[name] = hist
            self.bin_edges[name] = bin_edges
    
    def compute_psi(self, current_features: np.ndarray) -> DriftMetrics:
        """Compute PSI for current features vs reference."""
        with self._lock:
            feature_drifts = {}
            total_psi = 0.0
            
            for i, name in enumerate(self.feature_names):
                if name not in self.bin_edges:
                    continue
                
                feat_data = current_features[:, i]
                bin_edges = self.bin_edges[name]
                ref_hist = self.reference_distributions[name]
                
                # Compute current histogram
                curr_hist, _ = np.histogram(feat_data, bins=bin_edges, density=True)
                curr_hist = curr_hist + 1e-10
                curr_hist = curr_hist / curr_hist.sum()
                
                # PSI calculation
                psi = np.sum((curr_hist - ref_hist) * np.log(curr_hist / ref_hist))
                feature_drifts[name] = float(psi)
                total_psi += psi
            
            # KL divergence (on combined distribution)
            kl_div = 0.0
            if HAS_SCIPY:
                try:
                    # Sample combined distributions for KL
                    ref_combined = np.concatenate([
                        np.repeat(np.arange(len(h)), (h * 1000).astype(int))
                        for h in self.reference_distributions.values()
                    ])
                    curr_combined = np.concatenate([
                        np.repeat(np.arange(len(h)), (h * 1000).astype(int))
                        for h in [
                            np.histogram(current_features[:, i], bins=self.bin_edges[name], density=True)[0] + 1e-10
                            for i, name in enumerate(self.feature_names)
                            if name in self.bin_edges
                        ]
                    ])
                    if len(ref_combined) > 10 and len(curr_combined) > 10:
                        kl_div = float(stats.entropy(
                            np.bincount(curr_combined.astype(int)) / len(curr_combined),
                            np.bincount(ref_combined.astype(int)) / len(ref_combined)
                        ))
                except Exception:
                    pass
            
            alert = total_psi > self.psi_threshold
            
            return DriftMetrics(
                timestamp=time.time(),
                psi_score=float(total_psi),
                kl_divergence=float(kl_div),
                feature_drifts=feature_drifts,
                alert=alert,
            )
    
    def get_top_drifting_features(self, current_features: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get top-k features with highest PSI drift."""
        drift = self.compute_psi(current_features)
        sorted_features = sorted(drift.feature_drifts.items(), key=lambda x: x[1], reverse=True)
        return sorted_features[:top_k]


class ModelMonitor:
    """Main monitoring class integrating all tracking components."""
    
    def __init__(
        self,
        reference_features: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
        log_dir: Path = Path("monitoring_logs"),
        psi_threshold: float = 0.1,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.latency_tracker = LatencyTracker()
        self.confidence_tracker = ConfidenceTracker()
        self.drift_detector = None
        
        if reference_features is not None and feature_names is not None:
            self.drift_detector = DriftDetector(
                reference_features, feature_names, psi_threshold=psi_threshold
            )
        
        self._predictions_log_buffer = []
        self._log_flush_interval = 100
        self._lock = threading.Lock()
        
        # Start background flush thread
        self._flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self._flush_thread.start()
    
    def record_prediction(
        self,
        model_name: str,
        latency_ms: float,
        prediction: int,
        confidence: float,
        threat_type: str,
        features: Optional[np.ndarray] = None,
    ):
        """Record a prediction with all metrics."""
        timestamp = time.time()
        
        # Record metrics
        self.latency_tracker.record(model_name, latency_ms)
        self.confidence_tracker.record(confidence, prediction, model_name)
        
        # Log prediction
        features_hash = ""
        if features is not None:
            features_hash = str(hash(features.tobytes()))[:16]
        
        metric = PredictionMetrics(
            timestamp=timestamp,
            latency_ms=latency_ms,
            model_name=model_name,
            prediction=prediction,
            confidence=confidence,
            threat_type=threat_type,
            features_hash=features_hash,
        )
        
        with self._lock:
            self._predictions_log_buffer.append(asdict(metric))
            
            if len(self._predictions_log_buffer) >= self._log_flush_interval:
                self._flush_logs()
    
    def check_drift(self, features: np.ndarray) -> Optional[DriftMetrics]:
        """Check for data drift."""
        if self.drift_detector is None:
            return None
        
        drift = self.drift_detector.compute_psi(features)
        
        # Log drift metrics
        drift_log = {
            'type': 'drift',
            'timestamp': drift.timestamp,
            'psi_score': drift.psi_score,
            'kl_divergence': drift.kl_divergence,
            'alert': drift.alert,
            'top_drifting': self.drift_detector.get_top_drifting_features(features, 5),
        }
        
        with self._lock:
            self._predictions_log_buffer.append(drift_log)
        
        return drift
    
    def get_summary(self) -> Dict:
        """Get comprehensive monitoring summary."""
        return {
            'latency': {
                'overall': asdict(self.latency_tracker.get_stats()),
                'by_model': {name: asdict(stats) for name, stats in self.latency_tracker.get_all_model_stats().items()},
            },
            'confidence': {
                'overall': self.confidence_tracker.get_distribution(),
                'by_model': {name: self.confidence_tracker.get_distribution(name) for name in self.confidence_tracker._confidence_by_model},
                'by_class': self.confidence_tracker.get_class_conditional_distribution(),
            },
        }
    
    def _flush_logs(self):
        """Flush prediction logs to disk."""
        if not self._predictions_log_buffer:
            return
        
        log_file = self.log_dir / f"predictions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            for entry in self._predictions_log_buffer:
                # Convert numpy types to Python types
                clean_entry = {}
                for k, v in entry.items():
                    if isinstance(v, (np.integer, np.floating)):
                        clean_entry[k] = v.item()
                    elif isinstance(v, np.bool_):
                        clean_entry[k] = bool(v)
                    elif isinstance(v, np.ndarray):
                        clean_entry[k] = v.tolist()
                    else:
                        clean_entry[k] = v
                f.write(json.dumps(clean_entry) + '\n')
        
        self._predictions_log_buffer.clear()


    def _periodic_flush(self):
        while True:
            time.sleep(30)  # Flush every 30 seconds
            with self._lock:
                self._flush_logs()
    
    def save_summary(self, path: Optional[Path] = None):
        """Save monitoring summary to JSON."""
        if path is None:
            path = self.log_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        summary = self.get_summary()
        with open(path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return path


def demo():
    """Demo with synthetic data."""
    print("Generating reference data...")
    np.random.seed(42)
    n_ref = 5000
    n_feat = 20
    ref_features = np.random.randn(n_ref, n_feat)
    feature_names = [f"feat_{i}" for i in range(n_feat)]
    
    # Create monitor
    monitor = ModelMonitor(
        reference_features=ref_features,
        feature_names=feature_names,
        log_dir=Path("demo_monitoring"),
        psi_threshold=0.1,
    )
    
    print("Simulating predictions...")
    # Simulate normal predictions
    for _ in range(1000):
        feat = np.random.randn(n_feat)
        monitor.record_prediction(
            model_name="ensemble",
            latency_ms=np.random.exponential(5),
            prediction=np.random.randint(0, 2),
            confidence=np.random.beta(2, 5),  # Skewed toward low confidence
            threat_type="Trojan",
            features=feat,
        )
    
    # Check drift on normal data
    print("\nChecking drift on normal data...")
    drift = monitor.check_drift(ref_features[:1000])
    print(f"  PSI: {drift.psi_score:.4f}, Alert: {drift.alert}")
    
    # Simulate drift
    print("\nSimulating drifted data...")
    drifted_features = ref_features[:1000].copy()
    drifted_features[:, 0] += 2.0  # Shift feature 0
    drifted_features[:, 5] *= 3.0  # Scale feature 5
    
    drift = monitor.check_drift(drifted_features)
    print(f"  PSI: {drift.psi_score:.4f}, Alert: {drift.alert}")
    print(f"  Top drifting: {drift.feature_drifts}")
    
    # Get summary
    summary = monitor.get_summary()
    print("\n=== Monitoring Summary ===")
    print(json.dumps(summary, indent=2, default=str))
    
    # Save
    monitor.save_summary()
    print("\nLogs saved to demo_monitoring/")


if __name__ == "__main__":
    demo()