"""
Calibration Layer for Woodchopping Handicap Predictions

Three-component calibration system:
1. Isotonic Regression - Fix systematic bias
2. Variance Scaling - Competitor-specific uncertainty
3. Convergence Adjustment - Minimize finish-time spread for handicapping

Functions:
    IsotonicCalibrator - Bias correction via isotonic regression
    VarianceScaler - Predict competitor-specific variance
    apply_convergence_calibration - Minimize spread while preserving order
"""

from typing import Optional, Tuple, List, Dict
import pandas as pd
import numpy as np

from config import simulation_config

try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import mean_absolute_error
    import xgboost as xgb
    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False


class IsotonicCalibrator:
    """
    Isotonic regression calibrator for fixing systematic prediction bias.

    Learns a monotonic mapping from predicted times to actual times using
    validation data, correcting systematic over/under-prediction.
    """

    def __init__(self):
        self.calibrator_sb = None
        self.calibrator_uh = None
        self.is_fitted = False

    def fit(self, predictions: np.ndarray, actuals: np.ndarray, events: np.ndarray):
        """
        Fit isotonic calibrators for SB and UH events.

        Args:
            predictions: Predicted times
            actuals: Actual times
            events: Event codes ('SB' or 'UH')
        """
        if not CALIBRATION_AVAILABLE:
            return

        # Fit SB calibrator
        sb_mask = events == 'SB'
        if sb_mask.sum() > 10:  # Need minimum samples
            self.calibrator_sb = IsotonicRegression(out_of_bounds='clip')
            self.calibrator_sb.fit(predictions[sb_mask], actuals[sb_mask])

        # Fit UH calibrator
        uh_mask = events == 'UH'
        if uh_mask.sum() > 10:
            self.calibrator_uh = IsotonicRegression(out_of_bounds='clip')
            self.calibrator_uh.fit(predictions[uh_mask], actuals[uh_mask])

        self.is_fitted = True

    def calibrate(self, prediction: float, event_code: str) -> float:
        """Apply isotonic calibration to prediction"""
        if not self.is_fitted:
            return prediction

        if event_code == 'SB' and self.calibrator_sb is not None:
            return float(self.calibrator_sb.predict([prediction])[0])
        elif event_code == 'UH' and self.calibrator_uh is not None:
            return float(self.calibrator_uh.predict([prediction])[0])
        else:
            return prediction


class VarianceScaler:
    """
    Predict competitor-specific variance (uncertainty) using XGBoost.

    Trains on absolute residuals to predict std_dev per competitor,
    replacing uniform ±3s assumption with data-driven uncertainty.
    """

    def __init__(self):
        self.scaler_sb = None
        self.scaler_uh = None
        self.is_fitted = False

    def fit(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        events: np.ndarray,
        competitor_features: pd.DataFrame
    ):
        """
        Fit variance scalers for SB and UH events.

        Args:
            predictions: Predicted times
            actuals: Actual times
            events: Event codes
            competitor_features: DataFrame with competitor characteristics
                (variance_percentile, experience_level, etc.)
        """
        if not CALIBRATION_AVAILABLE:
            return

        # Calculate absolute residuals
        residuals = np.abs(predictions - actuals)

        # For each event, train XGBoost to predict residual magnitude
        for event in ['SB', 'UH']:
            mask = events == event
            if mask.sum() < 30:  # Need minimum samples
                continue

            X = competitor_features[mask]
            y = residuals[mask]

            # XGBoost for variance prediction
            model = xgb.XGBRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42
            )
            model.fit(X, y)

            if event == 'SB':
                self.scaler_sb = model
            else:
                self.scaler_uh = model

        self.is_fitted = True

    def predict_std_dev(
        self,
        competitor_features: Dict[str, float],
        event_code: str,
        baseline_std: float = 3.0
    ) -> float:
        """
        Predict competitor-specific std_dev.

        Args:
            competitor_features: Dict of feature values
            event_code: 'SB' or 'UH'
            baseline_std: Fallback std_dev if model unavailable

        Returns:
            Predicted std_dev clamped to [1.5s, 6.0s]
        """
        if not self.is_fitted:
            return baseline_std

        # Get appropriate model
        model = self.scaler_sb if event_code == 'SB' else self.scaler_uh
        if model is None:
            return baseline_std

        # Predict variance
        try:
            X = pd.DataFrame([competitor_features])
            predicted_std = model.predict(X)[0]

            # Combine with baseline (floor)
            final_std = max(predicted_std, baseline_std)

            # Clamp to reasonable range
            final_std = max(
                simulation_config.MIN_COMPETITOR_STD_SECONDS,
                min(final_std, simulation_config.MAX_COMPETITOR_STD_SECONDS)
            )

            return float(final_std)
        except Exception:
            return baseline_std


def apply_convergence_calibration(
    predictions: List[Tuple[str, float]],
    target_spread: float = 2.0,
    preserve_order: bool = True
) -> List[Tuple[str, float]]:
    """
    Apply convergence calibration to minimize finish-time spread for handicapping.

    This is Phase 3 of Baseline V2 calibration, adapted for ensemble predictions.

    Args:
        predictions: List of (competitor_name, predicted_time) tuples
        target_spread: Target finish-time spread in seconds
        preserve_order: If True, maintain ranking order (fastest -> slowest)

    Returns:
        List of (competitor_name, calibrated_time) tuples

    Note: Only apply during batch handicap generation, NOT during training
    (would bias accuracy metrics).
    """

    if len(predictions) < 2:
        return predictions

    # Extract times
    names = [p[0] for p in predictions]
    times = np.array([p[1] for p in predictions])

    # Calculate current spread
    current_spread = times.max() - times.min()

    if current_spread <= target_spread:
        # Already within target
        return predictions

    # Compress spread while preserving order
    median_time = np.median(times)

    if preserve_order:
        # Sort by time
        order = np.argsort(times)
        sorted_times = times[order]

        # Compress linearly toward median
        compression_factor = target_spread / current_spread
        calibrated_times = median_time + (sorted_times - median_time) * compression_factor

        # Restore original order
        result_times = np.zeros_like(times)
        result_times[order] = calibrated_times
    else:
        # Simple compression toward median
        compression_factor = target_spread / current_spread
        result_times = median_time + (times - median_time) * compression_factor

    # Return as list of tuples
    return list(zip(names, result_times.tolist()))


def calibrate_ensemble_prediction(
    prediction: float,
    std_dev: float,
    event_code: str,
    competitor_features: Dict[str, float],
    isotonic_calibrator: Optional[IsotonicCalibrator] = None,
    variance_scaler: Optional[VarianceScaler] = None
) -> Tuple[float, float]:
    """
    Apply full calibration pipeline to ensemble prediction.

    Args:
        prediction: Raw ensemble prediction
        std_dev: Raw ensemble std_dev estimate
        event_code: 'SB' or 'UH'
        competitor_features: Dict of competitor characteristics
        isotonic_calibrator: Fitted isotonic calibrator (optional)
        variance_scaler: Fitted variance scaler (optional)

    Returns:
        Tuple of (calibrated_time, calibrated_std_dev)
    """

    # 1. Isotonic regression for bias correction
    if isotonic_calibrator is not None and isotonic_calibrator.is_fitted:
        prediction = isotonic_calibrator.calibrate(prediction, event_code)

    # 2. Variance scaling for competitor-specific uncertainty
    if variance_scaler is not None and variance_scaler.is_fitted:
        std_dev = variance_scaler.predict_std_dev(competitor_features, event_code, baseline_std=std_dev)

    # Note: Convergence adjustment (step 3) applied later during batch handicap generation

    return prediction, std_dev
