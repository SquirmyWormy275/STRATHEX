"""
Ridge Regression Prediction Model for Woodchopping Handicap System

Ridge regression provides a fast, interpretable linear baseline with analytical
confidence intervals. Complements tree-based models in stacking ensemble.

Functions:
    train_ridge_model() - Train Ridge models for SB and UH events
    predict_time_ridge() - Predict time using trained Ridge model
"""

from typing import Dict, Optional, Tuple

import pandas as pd

from config import data_req, ml_config
from woodchopping.data import engineer_features_for_ml, load_results_df, standardize_results_data
from woodchopping.predictions.baseline import calculate_performance_weight

# ML Libraries
try:
    from sklearn.linear_model import Ridge, RidgeCV
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.preprocessing import StandardScaler

    RIDGE_AVAILABLE = True
except ImportError:
    RIDGE_AVAILABLE = False
    print("Warning: Ridge regression not available. Ridge predictions disabled.")

# Global cache for trained models
_cached_ridge_model_sb = None
_cached_ridge_model_uh = None
_cached_ridge_scaler_sb = None
_cached_ridge_scaler_uh = None
_ridge_training_data_size = 0


def train_ridge_model(
    results_df: Optional[pd.DataFrame] = None,
    force_retrain: bool = False,
    event_code: Optional[str] = None,
) -> Optional[Dict[str, Dict]]:
    """
    Train Ridge regression models for SB and UH events.

    Ridge advantages:
    - Fast training and prediction
    - Interpretable linear model (coefficients have direct meaning)
    - Analytical confidence intervals (no need for bootstrap)
    - RidgeCV auto-selects optimal regularization strength

    Uses 22 features (19 base + 3 polynomial):
    - All 19 standard features
    - diameter_cubic (additional non-linear term)
    - quality_squared (additional non-linear term)
    - hardness_x_gravity (additional interaction)

    Args:
        results_df: Historical results DataFrame
        force_retrain: Force retraining even if models are cached
        event_code: Specific event to train ('SB' or 'UH'), or None for both

    Returns:
        dict with 'SB' and 'UH' keys containing {'model': Ridge, 'scaler': StandardScaler}
    """
    global _cached_ridge_model_sb, _cached_ridge_model_uh
    global _cached_ridge_scaler_sb, _cached_ridge_scaler_uh
    global _ridge_training_data_size

    if not RIDGE_AVAILABLE:
        return None

    # Load data if not provided
    if results_df is None:
        results_df = load_results_df()

    if results_df is None or results_df.empty:
        return None

    # Standardize and engineer features
    results_df, _ = standardize_results_data(results_df)
    df_engineered = engineer_features_for_ml(results_df)

    if df_engineered is None or len(df_engineered) < data_req.MIN_ML_TRAINING_RECORDS_TOTAL:
        return None

    # Check cache
    if not force_retrain and _cached_ridge_model_sb is not None and _cached_ridge_model_uh is not None:
        if len(df_engineered) == _ridge_training_data_size:
            return {
                "SB": {"model": _cached_ridge_model_sb, "scaler": _cached_ridge_scaler_sb},
                "UH": {"model": _cached_ridge_model_uh, "scaler": _cached_ridge_scaler_uh},
            }

    # Add polynomial features for Ridge (total 22 features)
    df_engineered["diameter_cubic"] = df_engineered["size_mm"] ** 3
    df_engineered["quality_squared"] = df_engineered["wood_quality"] ** 2
    df_engineered["hardness_x_gravity"] = df_engineered["wood_janka_hardness"] * df_engineered["wood_spec_gravity"]

    feature_cols = list(ml_config.FEATURE_NAMES) + [
        "diameter_cubic",
        "quality_squared",
        "hardness_x_gravity",
    ]
    missing = [col for col in feature_cols if col not in df_engineered.columns]
    if missing:
        return None

    events_to_train = [event_code.upper()] if event_code else ["SB", "UH"]
    models = {}

    for event in events_to_train:
        event_df = df_engineered[df_engineered["event"] == event].copy()

        if len(event_df) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            continue

        X = event_df[feature_cols]
        y = event_df["raw_time"]

        # Time-decay weights
        sample_weights = event_df["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        sample_weights = sample_weights[mask]

        if len(X) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            continue

        # Standardize features (critical for Ridge regression)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # RidgeCV auto-selects optimal alpha via cross-validation
        alphas = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
        ridge_cv = RidgeCV(alphas=alphas, cv=5)
        ridge_cv.fit(X_scaled, y, sample_weight=sample_weights)

        # Train final model with best alpha
        model = Ridge(alpha=ridge_cv.alpha_)
        model.fit(X_scaled, y, sample_weight=sample_weights)

        models[event] = {"model": model, "scaler": scaler}

        # Cache models
        if event == "SB":
            _cached_ridge_model_sb = model
            _cached_ridge_scaler_sb = scaler
        else:
            _cached_ridge_model_uh = model
            _cached_ridge_scaler_uh = scaler

    _ridge_training_data_size = len(df_engineered)
    return models if models else None


def predict_time_ridge(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    return_ci: bool = False,
) -> Tuple[Optional[float], str, str, Optional[Tuple[float, float]]]:
    """
    Predict competitor time using Ridge regression model.

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (0-10)
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame
        return_ci: If True, return 95% confidence interval

    Returns:
        Tuple of (predicted_time, confidence, explanation, confidence_interval)
        confidence_interval is (lower, upper) if return_ci=True, else None
    """
    if not RIDGE_AVAILABLE:
        return None, "N/A", "Ridge regression not available", None

    # Train models if not cached
    models = train_ridge_model(results_df)
    if not models or event_code not in models:
        return None, "N/A", "Insufficient data for Ridge training", None

    # Engineer features for this prediction
    if results_df is None:
        results_df = load_results_df()

    results_df, _ = standardize_results_data(results_df)
    df_engineered = engineer_features_for_ml(results_df)

    if df_engineered is None:
        return None, "N/A", "Feature engineering failed", None

    # Add polynomial features
    df_engineered["diameter_cubic"] = df_engineered["size_mm"] ** 3
    df_engineered["quality_squared"] = df_engineered["wood_quality"] ** 2
    df_engineered["hardness_x_gravity"] = df_engineered["wood_janka_hardness"] * df_engineered["wood_spec_gravity"]

    # Get competitor's features
    competitor_data = df_engineered[df_engineered["competitor_name"] == competitor_name]
    if competitor_data.empty:
        return None, "LOW", "No historical data for competitor", None

    # Use most recent record's features as template
    latest = competitor_data.iloc[-1].copy()

    # Update with prediction parameters
    latest["size_mm"] = diameter
    latest["diameter_squared"] = diameter**2
    latest["diameter_cubic"] = diameter**3
    latest["wood_quality"] = quality
    latest["quality_squared"] = quality**2
    latest["quality_x_diameter"] = quality * diameter
    latest["quality_x_hardness"] = quality * latest["wood_janka_hardness"]
    latest["hardness_x_gravity"] = latest["wood_janka_hardness"] * latest["wood_spec_gravity"]

    feature_cols = list(ml_config.FEATURE_NAMES) + [
        "diameter_cubic",
        "quality_squared",
        "hardness_x_gravity",
    ]
    X_pred = latest[feature_cols].to_frame().T

    # Scale and predict
    model_dict = models[event_code]
    model = model_dict["model"]
    scaler = model_dict["scaler"]

    X_scaled = scaler.transform(X_pred)
    prediction = model.predict(X_scaled)[0]

    # Analytical confidence interval (simple approximation)
    ci = None
    if return_ci:
        # Estimate standard error from training residuals
        # This is a simplified version - full CI would require training data
        # For now, use rule of thumb: ±1.96 * 3s (assume ±3s std_dev)
        std_error = 3.0
        ci = (prediction - 1.96 * std_error, prediction + 1.96 * std_error)

    # Confidence based on number of samples
    n_samples = len(competitor_data)
    if n_samples >= 10:
        confidence = "HIGH"
    elif n_samples >= 5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    explanation = f"Ridge regression ({n_samples} samples, alpha={model.alpha:.1f})"

    return prediction, confidence, explanation, ci
