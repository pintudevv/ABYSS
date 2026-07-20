"""
Adversarial Robustness for ABYSS ML Models
===========================================
Implements:
- Feature-space PGD (Projected Gradient Descent) attacks
- Input sanitization / feature clipping
- Adversarial training pipeline
- Robustness evaluation
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable
import pickle


class FeatureSpacePGD:
    """
    Projected Gradient Descent attack in feature space.
    Since we work with pre-extracted EMBER features (2381 dims),
    we perturb the feature vector directly rather than raw bytes.
    """
    
    def __init__(
        self,
        model: Callable,
        eps: float = 0.1,
        alpha: float = 0.01,
        steps: int = 40,
        random_start: bool = True,
        clip_min: float = 0.0,
        clip_max: float = 1.0,
    ):
        """
        Args:
            model: Callable that takes features (n_samples, n_features) and returns logits/probs
            eps: Maximum L-inf perturbation budget
            alpha: Step size per iteration
            steps: Number of PGD iterations
            random_start: Whether to start from random point within eps-ball
            clip_min/max: Feature value bounds (for EMBER features, typically 0-1 after normalization)
        """
        self.model = model
        self.eps = eps
        self.alpha = alpha
        self.steps = steps
        self.random_start = random_start
        self.clip_min = clip_min
        self.clip_max = clip_max
    
    def __call__(self, X: np.ndarray, y: np.ndarray, targeted: bool = False) -> np.ndarray:
        """
        Generate adversarial examples.
        
        Args:
            X: Clean features (n_samples, n_features)
            y: True labels (for untargeted) or target labels (for targeted)
            targeted: If True, minimize loss for target class
            
        Returns:
            Adversarial examples (n_samples, n_features)
        """
        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.long)
        
        # Initialize adversarial examples
        if self.random_start:
            delta = torch.empty_like(X_tensor).uniform_(-self.eps, self.eps)
            X_adv = torch.clamp(X_tensor + delta, self.clip_min, self.clip_max)
        else:
            X_adv = X_tensor.clone()
        
        X_adv.requires_grad_(True)
        
        for step in range(self.steps):
            logits = self.model(X_adv)
            
            if targeted:
                loss = F.cross_entropy(logits, y_tensor)
            else:
                loss = F.cross_entropy(logits, y_tensor)
            
            # Gradient w.r.t. input
            grad = torch.autograd.grad(loss, X_adv, retain_graph=False, create_graph=False)[0]
            
            # PGD update
            with torch.no_grad():
                if targeted:
                    X_adv = X_adv - self.alpha * grad.sign()
                else:
                    X_adv = X_adv + self.alpha * grad.sign()
                
                # Project back to eps-ball
                delta = X_adv - X_tensor
                delta = torch.clamp(delta, -self.eps, self.eps)
                X_adv = torch.clamp(X_tensor + delta, self.clip_min, self.clip_max)
                
                # Re-enable gradients for next iteration
                X_adv.requires_grad_(True)
        
        return X_adv.detach().numpy()


class InputSanitizer:
    """
    Feature sanitization to mitigate adversarial perturbations.
    Applies clipping, smoothing, and outlier detection.
    """
    
    def __init__(
        self,
        clip_quantile: float = 0.999,
        noise_std: float = 0.0,
        median_filter: bool = False,
    ):
        """
        Args:
            clip_quantile: Clip features above this quantile (per feature)
            noise_std: Add small random noise to break gradient alignment
            median_filter: Apply median filter across similar features
        """
        self.clip_quantile = clip_quantile
        self.noise_std = noise_std
        self.median_filter = median_filter
        self.feature_max_ = None
    
    def fit(self, X: np.ndarray):
        """Learn clipping thresholds from clean data."""
        self.feature_max_ = np.quantile(X, self.clip_quantile, axis=0)
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """Apply sanitization."""
        X_clean = X.copy()
        
        # 1. Feature-wise clipping
        if self.feature_max_ is not None:
            X_clean = np.minimum(X_clean, self.feature_max_)
        
        # 2. Add noise (stochastic smoothing)
        if self.noise_std > 0:
            noise = np.random.normal(0, self.noise_std, X_clean.shape).astype(np.float32)
            X_clean = X_clean + noise
        
        # 3. Median filter (optional, for correlated features)
        if self.median_filter:
            from scipy.ndimage import median_filter
            X_clean = median_filter(X_clean, size=(1, 3))
        
        return X_clean
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


class AdversarialTrainer:
    """
    Adversarial training pipeline using PGD.
    Alternates between clean and adversarial examples.
    """
    
    def __init__(
        self,
        base_model,
        attack: FeatureSpacePGD,
        adversarial_ratio: float = 0.5,
    ):
        """
        Args:
            base_model: Sklearn-like model with fit/predict_proba
            attack: FeatureSpacePGD instance
            adversarial_ratio: Fraction of adversarial examples per batch
        """
        self.base_model = base_model
        self.attack = attack
        self.adversarial_ratio = adversarial_ratio
        self.is_fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray, X_val: np.ndarray = None, y_val: np.ndarray = None):
        """Train with adversarial examples."""
        n_adv = int(len(X) * self.adversarial_ratio)
        
        if n_adv > 0:
            # Generate adversarial examples
            indices = np.random.choice(len(X), n_adv, replace=False)
            X_adv = self.attack(X[indices], y[indices])
            
            # Combine clean + adversarial
            X_combined = np.vstack([X, X_adv])
            y_combined = np.hstack([y, y[indices]])
            
            # Shuffle
            perm = np.random.permutation(len(X_combined))
            X_combined = X_combined[perm]
            y_combined = y_combined[perm]
        else:
            X_combined, y_combined = X, y
        
        self.base_model.fit(X_combined, y_combined)
        self.is_fitted = True
        
        # Evaluate on validation if provided
        if X_val is not None and y_val is not None:
            clean_acc = self.base_model.score(X_val, y_val)
            adv_X_val = self.attack(X_val, y_val)
            adv_acc = self.base_model.score(adv_X_val, y_val)
            print(f"Clean accuracy: {clean_acc:.4f}")
            print(f"Adversarial accuracy: {adv_acc:.4f}")
        
        return self
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        return self.base_model.predict_proba(X)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Model not fitted")
        return self.base_model.predict(X)


class AdversarialEvaluator:
    """Evaluate model robustness against various attacks."""
    
    @staticmethod
    def _get_predictions(model, X: np.ndarray) -> np.ndarray:
        """Get class predictions from model."""
        if hasattr(model, 'predict'):
            return model.predict(X)
        elif hasattr(model, 'predict_proba'):
            return model.predict_proba(X).argmax(axis=1)
        else:
            # Assume PyTorch model
            model.eval()
            with torch.no_grad():
                X_tensor = torch.tensor(X, dtype=torch.float32)
                logits = model(X_tensor)
                return logits.argmax(dim=1).numpy()
    
    @staticmethod
    def evaluate(
        model,
        X: np.ndarray,
        y: np.ndarray,
        attacks: Dict[str, FeatureSpacePGD],
        sanitizer: Optional[InputSanitizer] = None,
    ) -> Dict[str, Dict]:
        """
        Evaluate model against multiple attacks.
        
        Returns:
            Dict with attack names as keys and metrics dict as values
        """
        results = {}
        
        # Clean accuracy
        clean_preds = AdversarialEvaluator._get_predictions(model, X)
        clean_acc = np.mean(clean_preds == y)
        results['clean'] = {'accuracy': clean_acc, 'clean_acc': clean_acc, 'adv_acc': clean_acc}
        
        for name, attack in attacks.items():
            print(f"Evaluating {name}...")
            X_adv = attack(X, y)
            
            if sanitizer:
                X_adv = sanitizer.transform(X_adv)
            
            adv_preds = AdversarialEvaluator._get_predictions(model, X_adv)
            adv_acc = np.mean(adv_preds == y)
            
            # Attack success rate (only on correctly classified clean samples)
            clean_correct = (clean_preds == y)
            if clean_correct.sum() > 0:
                attack_success = 1 - np.mean(adv_preds[clean_correct] == y[clean_correct])
            else:
                attack_success = 0.0
            
            results[name] = {
                'clean_acc': clean_acc,
                'adv_acc': adv_acc,
                'attack_success_rate': attack_success,
                'avg_l2': np.mean(np.linalg.norm(X_adv - X, axis=1)),
            }
            print(f"  {name}: acc={adv_acc:.4f}, attack_success={attack_success:.4f}")
        
        return results


def demo():
    """Quick demo of adversarial robustness using PyTorch MLP."""
    import torch.nn as nn
    import torch.optim as optim
    
    # Dummy data (replace with EMBER features)
    np.random.seed(42)
    X = np.random.randn(1000, 2381).astype(np.float32)
    y = np.random.randint(0, 2, 1000)
    
    # Train a simple PyTorch MLP (differentiable)
    class MLP(nn.Module):
        def __init__(self, input_dim=2381):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.ReLU(),
                nn.Linear(256, 64),
                nn.ReLU(),
                nn.Linear(64, 2)
            )
        def forward(self, x):
            return self.net(x)
    
    model = MLP()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    
    # Train
    X_tensor = torch.tensor(X[:800], dtype=torch.float32)
    y_tensor = torch.tensor(y[:800], dtype=torch.long)
    
    model.train()
    for epoch in range(20):
        optimizer.zero_grad()
        out = model(X_tensor)
        loss = criterion(out, y_tensor)
        loss.backward()
        optimizer.step()
    
    model.eval()
    with torch.no_grad():
        X_test = torch.tensor(X[800:], dtype=torch.float32)
        y_test = torch.tensor(y[800:], dtype=torch.long)
        preds = model(X_test).argmax(dim=1)
        clean_acc = (preds == y_test).float().mean().item()
        print(f"Clean accuracy: {clean_acc:.4f}")
    
    # Create attack
    attack = FeatureSpacePGD(
        model=model,
        eps=0.1,
        alpha=0.01,
        steps=20,
        clip_min=-5.0,
        clip_max=5.0,
    )
    
    # Evaluate
    evaluator = AdversarialEvaluator()
    attacks = {'pgd_01': attack}
    results = evaluator.evaluate(model, X[800:], y[800:], attacks)
    
    print("\n=== Adversarial Evaluation ===")
    for name, res in results.items():
        print(f"{name}: {res}")
    
    # Test sanitizer
    sanitizer = InputSanitizer(clip_quantile=0.99, noise_std=0.01)
    sanitizer.fit(X[:800])
    
    X_adv = attack(X[800:900], y[800:900])
    X_sanitized = sanitizer.transform(X_adv)
    
    model.eval()
    with torch.no_grad():
        adv_preds = model(torch.tensor(X_adv, dtype=torch.float32)).argmax(dim=1)
        san_preds = model(torch.tensor(X_sanitized, dtype=torch.float32)).argmax(dim=1)
    
    print(f"\nAdversarial accuracy: {(adv_preds.numpy() == y[800:900]).mean():.4f}")
    print(f"Sanitized accuracy: {(san_preds.numpy() == y[800:900]).mean():.4f}")


if __name__ == "__main__":
    demo()