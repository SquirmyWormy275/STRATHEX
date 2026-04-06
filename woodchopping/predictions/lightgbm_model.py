"""
LightGBM Prediction Model for Woodchopping Handicap System

LightGBM uses leaf-wise tree growth (vs XGBoost's depth-wise), better handles
categorical features, and provides diverse predictions for ensemble stacking.

Functions:
    train_lightgbm_model() - Train LightGBM models for SB and UH events
    predict_time_lightgbm() - Predict time using trained LightGBM model
"""

from typing import Dict, Optional, Tuple

import pandas as pd

from config import data_req, ml_config
from woodchopping.data import engineer_features_for_ml, load_results_df, standardize_results_data
from woodchopping.predictions.baseline import calculate_performance_weight

# ML Libraries
try:
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import TimeSeriesSplit

    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("Warning: LightGBM not available. LightGBM predictions disabled.")

# Global cache for trained models
_cached_lgb_model_sb = None
_cached_lgb_model_uh = None
_lgb_training_data_size = 0


def train_lightgbm_model(
    results_df: Optional[pd.DataFrame] = None,
    force_retrain: bool = False,
    event_code: Optional[str] = None,
) -> Optional[Dict[str, object]]:
    """
    Train LightGBM models for SB and UH events.

    LightGBM uses leaf-wise tree growth which can achieve better accuracy
    on small datasets compared to XGBoost's depth-wise approach.

    Args:
        results_df: Historical results DataFrame
        force_retrain: Force retraining even if models are cached
        event_code: Specific event to train ('SB' or 'UH'), or None for both

    Returns:
        dict with 'SB' and 'UH' keys containing trained models, or None if insufficient data
    """
    global _cached_lgb_model_sb, _cached_lgb_model_uh, _lgb_training_data_size

    if not LIGHTGBM_AVAILABLE:
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
    if not force_retrain and _cached_lgb_model_sb is not None and _cached_lgb_model_uh is not None:
        if len(df_engineered) == _lgb_training_data_size:
            return {"SB": _cached_lgb_model_sb, "UH": _cached_lgb_model_uh}

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

        # Time-decay weights
        sample_weights = event_df["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        sample_weights = sample_weights[mask]

        if len(X) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            continue

        # LightGBM parameters (optimized for small datasets)
        lgb_params = {
            "objective": "regression",
            "metric": "mae",
            "boosting_type": "gbdt",
            "num_leaves": 63,  # 2^6 - 1 (deeper than XGBoost max_depth=4)
            "learning_rate": 0.05,
            "n_estimators": 250,
            "feature_fraction": 0.8,  # Use 80% features per tree
            "bagging_fraction": 0.8,  # Use 80% data per tree
            "bagging_freq": 5,
            "min_data_in_leaf": 10,
            "lambda_l1": 0.1,  # L1 regularization
            "lambda_l2": 0.1,  # L2 regularization
            "random_state": ml_config.RANDOM_STATE,
            "verbose": -1,
        }

        # Train model with time-decay weights
        model = lgb.LGBMRegressor(**lgb_params)
        model.fit(X, y, sample_weight=sample_weights)

        models[event] = model

        # Cache models
        if event == "SB":
            _cached_lgb_model_sb = model
        else:
            _cached_lgb_model_uh = model

    _lgb_training_data_size = len(df_engineered)
    return models if models else None


def predict_time_lightgbm(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
) -> Tuple[Optional[float], str, str]:
    """
    Predict competitor time using LightGBM model.

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (0-10)
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame

    Returns:
        Tuple of (predicted_time, confidence, explanation)
    """
    if not LIGHTGBM_AVAILABLE:
        return None, "N/A", "LightGBM not available"

    # Train models if not cached
    models = train_lightgbm_model(results_df)
    if not models or event_code not in models:
        return None, "N/A", "Insufficient data for LightGBM training"

    # Engineer features for this prediction
    if results_df is None:
        results_df = load_results_df()

    results_df, _ = standardize_results_data(results_df)
    df_engineered = engineer_features_for_ml(results_df)

    if df_engineered is None:
        return None, "N/A", "Feature engineering failed"

    # Get competitor's features
    competitor_data = df_engineered[df_engineered["competitor_name"] == competitor_name]
    if competitor_data.empty:
        return None, "LOW", "No historical data for competitor"

    # Use most recent record's features as template
    latest = competitor_data.iloc[-1].copy()

    # Update with prediction parameters
    latest["size_mm"] = diameter
    latest["diameter_squared"] = diameter**2
    latest["wood_quality"] = quality

    feature_cols = list(ml_config.FEATURE_NAMES)
    X_pred = latest[feature_cols].to_frame().T

    # Predict
    model = models[event_code]
    prediction = model.predict(X_pred)[0]

    # Confidence based on number of samples
    n_samples = len(competitor_data)
    if n_samples >= 10:
        confidence = "HIGH"
    elif n_samples >= 5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    explanation = f"LightGBM prediction ({n_samples} historical samples)"

    return prediction, confidence, explanation
