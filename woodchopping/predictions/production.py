"""
Production Integration for Woodchopping Handicap System

Provides versioning, monitoring, A/B testing, and drift detection infrastructure
for production deployment of the stacking ensemble.

Features:
- Model versioning and registry
- Performance monitoring
- Feature drift detection
- A/B testing framework
- Automatic retraining triggers
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from scipy.stats import ks_2samp

    STATS_AVAILABLE = True
except ImportError:
    STATS_AVAILABLE = False


# Model Registry
MODEL_REGISTRY = {
    "baseline_v2_hybrid": {
        "version": "2.0",
        "mae": 3.58,
        "active": True,
        "description": "Hierarchical regression + convergence calibration",
    },
    "xgboost_enhanced": {
        "version": "2.0",
        "mae": None,  # TBD from validation
        "active": True,
        "description": "XGBoost with 19 features + Bayesian optimization",
    },
    "stacking_ensemble": {
        "version": "1.0",
        "mae": None,  # TBD from validation
        "active": False,  # Enable after validation
        "description": "Hierarchical stacking of 6 base models",
    },
}


class PerformanceMonitor:
    """Monitor prediction accuracy and detect degradation"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.predictions = []
        self.actuals = []
        self.timestamps = []

    def log_prediction(self, prediction: float, actual: Optional[float] = None):
        """Log a prediction and actual result"""
        self.predictions.append(prediction)
        self.actuals.append(actual if actual is not None else np.nan)
        self.timestamps.append(datetime.now())

        # Keep only recent window
        if len(self.predictions) > self.window_size:
            self.predictions = self.predictions[-self.window_size :]
            self.actuals = self.actuals[-self.window_size :]
            self.timestamps = self.timestamps[-self.window_size :]

    def get_rolling_mae(self) -> Optional[float]:
        """Calculate rolling MAE over window"""
        # Filter out predictions without actuals
        pairs = [(p, a) for p, a in zip(self.predictions, self.actuals) if not np.isnan(a)]

        if len(pairs) < 10:
            return None

        preds = np.array([p for p, a in pairs])
        acts = np.array([a for p, a in pairs])

        return float(np.mean(np.abs(preds - acts)))

    def check_degradation(self, baseline_mae: float, threshold: float = 0.20) -> bool:
        """
        Check if performance has degraded by threshold percentage.

        Args:
            baseline_mae: Expected baseline MAE
            threshold: Alert if degradation > threshold (default 20%)

        Returns:
            True if degradation detected
        """
        current_mae = self.get_rolling_mae()
        if current_mae is None:
            return False

        degradation = (current_mae - baseline_mae) / baseline_mae
        return degradation > threshold


class DriftDetector:
    """Detect feature distribution drift"""

    def __init__(self):
        self.baseline_features = None

    def set_baseline(self, features_df: pd.DataFrame):
        """Set baseline feature distributions from training data"""
        self.baseline_features = features_df.copy()

    def detect_drift(self, new_features_df: pd.DataFrame, alpha: float = 0.05) -> Dict[str, bool]:
        """
        Detect distribution drift using Kolmogorov-Smirnov test.

        Args:
            new_features_df: Recent feature data
            alpha: Significance level (default 0.05)

        Returns:
            Dict mapping feature names to drift detected (True/False)
        """
        if not STATS_AVAILABLE or self.baseline_features is None:
            return {}

        drift_results = {}

        for col in new_features_df.columns:
            if col not in self.baseline_features.columns:
                continue

            baseline_vals = self.baseline_features[col].dropna()
            new_vals = new_features_df[col].dropna()

            if len(baseline_vals) < 10 or len(new_vals) < 10:
                continue

            # Kolmogorov-Smirnov test
            statistic, p_value = ks_2samp(baseline_vals, new_vals)

            # Drift detected if p < alpha
            drift_results[col] = p_value < alpha

        return drift_results


class ABTester:
    """A/B testing framework for model comparison"""

    def __init__(self, model_a: str, model_b: str, split_ratio: float = 0.5):
        """
        Args:
            model_a: Name of model A
            model_b: Name of model B
            split_ratio: Fraction assigned to model A (default 0.5)
        """
        self.model_a = model_a
        self.model_b = model_b
        self.split_ratio = split_ratio
        self.results_a = []
        self.results_b = []

    def assign_model(self, competitor_name: str) -> str:
        """Deterministically assign competitor to A or B based on hash"""
        # Use hash for stable assignment
        hash_val = hash(competitor_name)
        return self.model_a if (hash_val % 100) < (self.split_ratio * 100) else self.model_b

    def log_result(self, model: str, prediction: float, actual: float):
        """Log prediction result"""
        error = abs(prediction - actual)

        if model == self.model_a:
            self.results_a.append(error)
        elif model == self.model_b:
            self.results_b.append(error)

    def get_comparison(self) -> Dict:
        """Get A/B test comparison results"""
        if len(self.results_a) < 10 or len(self.results_b) < 10:
            return {"status": "insufficient_data"}

        mae_a = np.mean(self.results_a)
        mae_b = np.mean(self.results_b)

        improvement = (mae_a - mae_b) / mae_a * 100

        return {
            "status": "ready",
            "model_a": self.model_a,
            "model_b": self.model_b,
            "mae_a": mae_a,
            "mae_b": mae_b,
            "improvement_pct": improvement,
            "n_samples_a": len(self.results_a),
            "n_samples_b": len(self.results_b),
            "winner": self.model_a if mae_a < mae_b else self.model_b,
        }


def predict_with_versioning(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    model_version: str = "stacking_ensemble",
    fallback: str = "baseline_v2_hybrid",
) -> Tuple[Optional[float], str, str]:
    """
    Make prediction with model versioning and fallback.

    Args:
        competitor_name: Competitor's name
        species: Wood species
        diameter: Block diameter
        quality: Wood quality
        event_code: Event type
        model_version: Model to use (default 'stacking_ensemble')
        fallback: Fallback model if primary fails

    Returns:
        Tuple of (prediction, confidence, explanation)
    """

    # Check if model is active
    if model_version not in MODEL_REGISTRY:
        print(f"Unknown model version: {model_version}, using fallback")
        model_version = fallback

    if not MODEL_REGISTRY[model_version]["active"]:
        print(f"Model {model_version} not active, using fallback {fallback}")
        model_version = fallback

    try:
        # Route to appropriate model
        if model_version == "stacking_ensemble":
            from woodchopping.predictions.stacking_ensemble import StackingEnsemble

            ensemble = StackingEnsemble()
            result = ensemble.predict(competitor_name, species, diameter, quality, event_code)
            return result.time, result.confidence, result.explanation

        elif model_version == "baseline_v2_hybrid":
            from woodchopping.data import load_results_df, load_wood_data
            from woodchopping.predictions.baseline import predict_baseline_v2_hybrid

            time, conf, exp, _ = predict_baseline_v2_hybrid(
                competitor_name,
                species,
                diameter,
                quality,
                event_code,
                load_results_df(),
                load_wood_data(),
            )
            return time, conf, exp

        elif model_version == "xgboost_enhanced":
            # Placeholder - would call enhanced XGBoost predict function
            return None, "N/A", "XGBoost enhanced not yet implemented"

    except Exception as e:
        print(f"Model {model_version} failed: {e}, falling back to {fallback}")
        if fallback != model_version:
            return predict_with_versioning(
                competitor_name,
                species,
                diameter,
                quality,
                event_code,
                model_version=fallback,
                fallback="baseline_v2_hybrid",
            )
        else:
            return None, "N/A", f"All models failed: {e}"


def trigger_retraining(
    reason: str,
    new_results_count: Optional[int] = None,
    degradation_pct: Optional[float] = None,
    drift_features: Optional[List[str]] = None,
):
    """
    Trigger model retraining based on conditions.

    Args:
        reason: Reason for retraining
        new_results_count: Number of new results since last training
        degradation_pct: Performance degradation percentage
        drift_features: List of features with detected drift
    """

    print(f"\n{'=' * 70}")
    print(f"RETRAINING TRIGGER: {reason}")
    print(f"{'=' * 70}")

    if new_results_count:
        print(f"  New results: {new_results_count}")
    if degradation_pct:
        print(f"  Performance degradation: {degradation_pct:.1%}")
    if drift_features:
        print(f"  Features with drift: {', '.join(drift_features)}")

    print("\nAction required: Retrain models with updated data")
    print(f"{'=' * 70}\n")


# Auto-monitoring configuration
AUTO_RETRAIN_CONFIG = {
    "new_results_threshold": 50,  # Retrain after 50 new results
    "degradation_threshold": 0.20,  # Retrain if MAE degrades >20%
    "drift_alpha": 0.05,  # Drift detection significance level
}
