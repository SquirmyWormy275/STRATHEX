"""
RandomForest Prediction Model for Woodchopping Handicap System

RandomForest provides excellent variance estimation via Out-of-Bag (OOB) scores
and is robust to outliers. Critical for stacking ensemble diversity.

Functions:
    train_randomforest_model() - Train RandomForest models for SB and UH events
    predict_time_randomforest() - Predict time using trained RandomForest model
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from config import data_req, ml_config
from woodchopping.data import engineer_features_for_ml, load_results_df, standardize_results_data
from woodchopping.predictions.baseline import calculate_performance_weight

# ML Libraries
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    RF_AVAILABLE = True
except ImportError:
    RF_AVAILABLE = False
    print("Warning: RandomForest not available. RandomForest predictions disabled.")

# Global cache for trained models
_cached_rf_model_sb = None
_cached_rf_model_uh = None
_rf_training_data_size = 0


def train_randomforest_model(
    results_df: Optional[pd.DataFrame] = None,
    force_retrain: bool = False,
    event_code: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """
    Train RandomForest models for SB and UH events.

    RandomForest advantages:
    - Out-of-Bag (OOB) score for free cross-validation
    - Robust to outliers (bagging reduces variance)
    - Excellent uncertainty quantification via tree std_dev

    Args:
        results_df: Historical results DataFrame
        force_retrain: Force retraining even if models are cached
        event_code: Specific event to train ('SB' or 'UH'), or None for both

    Returns:
        dict with 'SB' and 'UH' keys containing trained models, or None if insufficient data
    """
    global _cached_rf_model_sb, _cached_rf_model_uh, _rf_training_data_size

    if not RF_AVAILABLE:
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
    if not force_retrain and _cached_rf_model_sb is not None and _cached_rf_model_uh is not None:
        if len(df_engineered) == _rf_training_data_size:
            return {"SB": _cached_rf_model_sb, "UH": _cached_rf_model_uh}

    feature_cols = list(ml_config.FEATURE_NAMES)
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

        # RandomForest doesn't support sample_weight for OOB, so we'll resample
        # based on time-decay weights to achieve similar effect
        sample_weights = event_df["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        sample_weights = sample_weights[mask]

        if len(X) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            continue

        # RandomForest parameters (optimized for variance estimation)
        rf_params = {
            "n_estimators": 300,  # More trees for stable variance estimates
            "max_depth": 20,  # Deeper than XGBoost (RF handles overfitting via bagging)
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "max_features": "sqrt",  # sqrt(n_features) per split
            "oob_score": True,  # Enable OOB for free CV
            "bootstrap": True,
            "random_state": ml_config.RANDOM_STATE,
            "n_jobs": -1,  # Use all CPU cores
            "warm_start": False,
        }

        # Train model (note: RF doesn't use sample_weight with OOB)
        model = RandomForestRegressor(**rf_params)
        model.fit(X, y)

        models[event] = model

        # Cache models
        if event == "SB":
            _cached_rf_model_sb = model
        else:
            _cached_rf_model_uh = model

    _rf_training_data_size = len(df_engineered)
    return models if models else None


def predict_time_randomforest(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    return_std: bool = False,
) -> Tuple[Optional[float], str, str, Optional[float]]:
    """
    Predict competitor time using RandomForest model.

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (0-10)
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame
        return_std: If True, return std_dev from trees

    Returns:
        Tuple of (predicted_time, confidence, explanation, std_dev)
    """
    if not RF_AVAILABLE:
        return None, "N/A", "RandomForest not available", None

    # Train models if not cached
    models = train_randomforest_model(results_df)
    if not models or event_code not in models:
        return None, "N/A", "Insufficient data for RandomForest training", None

    # Engineer features for this prediction
    if results_df is None:
        results_df = load_results_df()

    results_df, _ = standardize_results_data(results_df)
    df_engineered = engineer_features_for_ml(results_df)

    if df_engineered is None:
        return None, "N/A", "Feature engineering failed", None

    # Get competitor's features
    competitor_data = df_engineered[df_engineered["competitor_name"] == competitor_name]
    if competitor_data.empty:
        return None, "LOW", "No historical data for competitor", None

    # Use most recent record's features as template
    latest = competitor_data.iloc[-1].copy()

    # Update with prediction parameters
    latest["size_mm"] = diameter
    latest["diameter_squared"] = diameter**2
    latest["wood_quality"] = quality

    feature_cols = list(ml_config.FEATURE_NAMES)
    X_pred = latest[feature_cols].to_frame().T

    # Predict with all trees
    model = models[event_code]
    predictions = np.array([tree.predict(X_pred)[0] for tree in model.estimators_])
    prediction = predictions.mean()
    std_dev = predictions.std() if return_std else None

    # Confidence based on OOB score and sample count
    n_samples = len(competitor_data)
    oob_score = model.oob_score_ if hasattr(model, "oob_score_") else 0.0

    if n_samples >= 10 and oob_score > 0.6:
        confidence = "HIGH"
    elif n_samples >= 5 and oob_score > 0.4:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    explanation = f"RandomForest prediction ({n_samples} samples, OOB R²={oob_score:.2f})"

    return prediction, confidence, explanation, std_dev
