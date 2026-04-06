"""
Machine Learning Prediction Model for Woodchopping Handicap System

This module provides XGBoost-based time prediction using historical performance data.
Separate models are trained for Standing Block (SB) and Underhand (UH) events.

Functions:
    train_ml_model() - Train XGBoost models for SB and UH events
    predict_time_ml() - Predict time using trained ML model
    perform_cross_validation() - K-fold cross-validation for model accuracy
    display_feature_importance() - Display feature importance rankings
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

# Import config
from config import data_req, ml_config

# Import local data modules
from woodchopping.data import (
    engineer_features_for_ml,
    load_results_df,
    load_wood_data,
    standardize_results_data,
    validate_results_data,
)

# Import time-decay weighting function
from woodchopping.predictions.baseline import calculate_performance_weight

# ML Libraries
try:
    import xgboost as xgb
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: XGBoost/scikit-learn not available. ML predictions disabled.")


# Global cache for trained models
_cached_ml_model_sb = None
_cached_ml_model_uh = None
_model_training_data_size = 0
_feature_importance_sb = None
_feature_importance_uh = None
_model_cv_metrics_sb = None
_model_cv_metrics_uh = None


def perform_cross_validation(
    X, y, model_params: dict, cv_folds: int = 5, dates: Optional[pd.Series] = None
) -> Optional[dict]:
    """
    Perform k-fold cross-validation to estimate model accuracy.

    Args:
        X: Feature matrix
        y: Target vector
        model_params: XGBoost parameters dict
        cv_folds: Number of cross-validation folds

    Returns:
        dict: CV results with mean and std of metrics
            {
                'mae_mean': float,
                'mae_std': float,
                'r2_mean': float,
                'r2_std': float,
                'mae_scores': array,
                'r2_scores': array
            }
        Returns None if ML libraries not available
    """
    if not ML_AVAILABLE:
        return None

    # Create model with same params as training
    model = xgb.XGBRegressor(**model_params)

    if dates is not None and len(dates) >= cv_folds * 2:
        # Time-aware CV to reduce leakage
        order = np.argsort(dates.values)
        X_sorted = X.iloc[order]
        y_sorted = y.iloc[order]

        tss = TimeSeriesSplit(n_splits=cv_folds)
        mae_scores = []
        r2_scores = []

        for train_idx, test_idx in tss.split(X_sorted):
            cv_model = xgb.XGBRegressor(**model_params)
            cv_model.fit(X_sorted.iloc[train_idx], y_sorted.iloc[train_idx])
            preds = cv_model.predict(X_sorted.iloc[test_idx])
            mae_scores.append(mean_absolute_error(y_sorted.iloc[test_idx], preds))
            r2_scores.append(r2_score(y_sorted.iloc[test_idx], preds))

        mae_scores = np.array(mae_scores)
        r2_scores = np.array(r2_scores)

        return {
            "mae_mean": mae_scores.mean(),
            "mae_std": mae_scores.std(),
            "r2_mean": r2_scores.mean(),
            "r2_std": r2_scores.std(),
            "mae_scores": mae_scores,
            "r2_scores": r2_scores,
        }

    # Perform cross-validation for MAE
    mae_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="neg_mean_absolute_error", n_jobs=-1)

    # Perform cross-validation for R²
    r2_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="r2", n_jobs=-1)

    return {
        "mae_mean": -mae_scores.mean(),
        "mae_std": mae_scores.std(),
        "r2_mean": r2_scores.mean(),
        "r2_std": r2_scores.std(),
        "mae_scores": -mae_scores,
        "r2_scores": r2_scores,
    }


def display_feature_importance(model, event_code: str, feature_names: list) -> None:
    """
    Display feature importance from trained XGBoost model.

    Args:
        model: Trained XGBoost model
        event_code: 'SB' or 'UH'
        feature_names: List of feature names
    """
    global _feature_importance_sb, _feature_importance_uh

    if model is None:
        return

    importance = model.feature_importances_

    # Sort by importance
    importance_pairs = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

    print(f"\n{'=' * 70}")
    print(f"  FEATURE IMPORTANCE - {event_code} MODEL")
    print(f"{'=' * 70}")
    print(f"\n{'Feature':<40} {'Importance':>10}")
    print("-" * 70)

    for name, score in importance_pairs:
        # Create a simple bar chart
        bar_length = int(score * 40)
        bar = "#" * bar_length
        print(f"{name:<40} {score:>9.3f}  {bar}")

    print(f"{'=' * 70}")

    # Store for later reference
    if event_code == "SB":
        _feature_importance_sb = dict(importance_pairs)
    else:
        _feature_importance_uh = dict(importance_pairs)


def train_ml_model(
    results_df: Optional[pd.DataFrame] = None,
    wood_df: Optional[pd.DataFrame] = None,
    force_retrain: bool = False,
    event_code: Optional[str] = None,
    skip_validation: bool = False,
    verbose: bool = True,
    show_feature_importance: bool = True,
) -> Optional[Dict[str, object]]:
    """
    Train separate XGBoost models for SB and UH events.

    Args:
        results_df: Historical results DataFrame (will load if not provided)
        wood_df: Wood properties DataFrame (will load if not provided)
        force_retrain: Force retraining even if models are cached
        event_code: Specific event to train ('SB' or 'UH'), or None for both
        skip_validation: If True, assumes results_df is already validated
        verbose: If True, print training progress and metrics
        show_feature_importance: If True, print feature importance table

    Returns:
        dict with 'SB' and 'UH' keys containing trained models, or None if insufficient data

    Example:
        >>> models = train_ml_model()
        >>> if models:
        ...     sb_model = models['SB']
        ...     uh_model = models['UH']
    """
    global _cached_ml_model_sb, _cached_ml_model_uh, _model_training_data_size
    global _feature_importance_sb, _feature_importance_uh
    global _model_cv_metrics_sb, _model_cv_metrics_uh

    def _log(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    # Check if ML libraries available
    if not ML_AVAILABLE:
        return None

    # Load data if not provided
    if results_df is None:
        results_df = load_results_df()

    if results_df is None or results_df.empty:
        return None

    if skip_validation:
        validated_df = results_df
    else:
        # Validate and clean data
        _log("\n[DATA VALIDATION]")
        validated_df, warnings = validate_results_data(results_df)

        if warnings:
            _log(f"Data validation warnings ({len(warnings)} issues):")
            for i, warning in enumerate(warnings[:5], 1):  # Show first 5
                _log(f"  {i}. {warning}")
            if len(warnings) > 5:
                _log(f"  ... and {len(warnings) - 5} more")

        if validated_df is None or validated_df.empty:
            _log("ERROR: No valid data after validation")
            return None

        _log(f"Valid records: {len(validated_df)} / {len(results_df)} ({len(results_df) - len(validated_df)} removed)")

    # Check if we can use cached models
    if not force_retrain and _cached_ml_model_sb is not None and _cached_ml_model_uh is not None:
        if len(validated_df) == _model_training_data_size:
            return {"SB": _cached_ml_model_sb, "UH": _cached_ml_model_uh}

    # Engineer features
    df_engineered = engineer_features_for_ml(validated_df, wood_df)

    if df_engineered is None or len(df_engineered) < data_req.MIN_ML_TRAINING_RECORDS_TOTAL:
        _log(
            f"Insufficient data for ML training: {len(df_engineered) if df_engineered is not None else 0} records (need {data_req.MIN_ML_TRAINING_RECORDS_TOTAL}+)"
        )
        return None

    # Define features and target
    feature_cols = list(ml_config.FEATURE_NAMES)

    # Ensure all feature columns exist
    missing = [col for col in feature_cols if col not in df_engineered.columns]
    if missing:
        _log(f"Warning: Missing feature columns: {missing}")
        return None

    # Determine which events to train
    events_to_train = []
    if event_code:
        events_to_train = [event_code.upper()]
    else:
        events_to_train = ["SB", "UH"]

    models = {}

    for event in events_to_train:
        _log(f"\n[TRAINING {event} MODEL]")

        # Filter data for this event
        event_df = df_engineered[df_engineered["event"] == event].copy()

        if len(event_df) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            _log(
                f"Insufficient {event} data: {len(event_df)} records (need {data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT}+)"
            )
            continue

        X = event_df[feature_cols]
        y = event_df["raw_time"]

        # Calculate TIME-DECAY WEIGHTS for each training sample
        # Recent performances get higher weight during training
        # Critical for aging competitors: their 10-year-old peak performances shouldn't dominate the model
        sample_weights = event_df["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))

        # Remove any rows with NaN values
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        sample_weights = sample_weights[mask]

        if len(X) < data_req.MIN_ML_TRAINING_RECORDS_PER_EVENT:
            _log(f"Insufficient valid {event} data after cleaning: {len(X)} records")
            continue

        # Report on time-decay weighting effectiveness
        avg_weight = sample_weights.mean()
        recent_fraction = (sample_weights > 0.5).sum() / len(sample_weights)
        _log(f"  Time-decay: avg weight {avg_weight:.2f}, {recent_fraction * 100:.0f}% of data from last 2 years")

        # Model parameters
        # Monotonic constraints by feature name (dict form is compatible with newer XGBoost)
        # +1 = increasing (higher feature -> higher time), -1 = decreasing, 0 = unconstrained
        monotone_map = {
            # Original 7 features
            "competitor_avg_time_by_event": 1,  # Higher avg -> higher time
            "event_encoded": 0,  # SB vs UH (unconstrained)
            "size_mm": 1,  # Larger diameter -> higher time
            "wood_janka_hardness": 1,  # Harder wood -> higher time
            "wood_spec_gravity": 1,  # Denser wood -> higher time
            "competitor_experience": 0,  # Experience can go either way
            "competitor_trend_slope": 1,  # Positive slope (getting slower) -> higher time
            # NEW features (12 added)
            "wood_quality": 1,  # Higher quality (harder) -> higher time
            "diameter_squared": 1,  # Larger blocks exponentially harder
            "quality_x_diameter": 1,  # Harder large blocks -> higher time
            "quality_x_hardness": 1,  # Hard species + hard quality -> higher time
            "experience_x_size": 0,  # Complex interaction (unconstrained)
            "competitor_variance": 0,  # Consistency doesn't directly affect mean time
            "competitor_median_diameter": 0,  # Selection bias proxy (unconstrained)
            "recency_score": 0,  # Days since last comp (unconstrained - could be momentum or rust)
            "career_phase": 0,  # -1/0/+1 categorical (unconstrained)
            "seasonal_month_sin": 0,  # Cyclical (unconstrained)
            "seasonal_month_cos": 0,  # Cyclical (unconstrained)
            "event_x_diameter": 0,  # Interaction (unconstrained - different for SB vs UH)
        }
        monotone_constraints = {name: monotone_map.get(name, 0) for name in feature_cols}

        model_params = {
            "n_estimators": ml_config.N_ESTIMATORS,
            "max_depth": ml_config.MAX_DEPTH,
            "learning_rate": ml_config.LEARNING_RATE,
            "random_state": ml_config.RANDOM_STATE,
            "objective": ml_config.OBJECTIVE,
            "tree_method": ml_config.TREE_METHOD,
            "monotone_constraints": monotone_constraints,
        }

        # Perform cross-validation (without weights for simplicity)
        # Note: Could add weighted CV in future if needed
        _log(f"Cross-validating {event} model (5-fold)...")
        dates = None
        if "date" in event_df.columns:
            dates = pd.to_datetime(event_df["date"], errors="coerce")
            if dates.isna().any():
                dates = None
        cv_results = perform_cross_validation(X, y, model_params, cv_folds=ml_config.CV_FOLDS, dates=dates)

        if cv_results:
            _log(f"  CV MAE: {cv_results['mae_mean']:.2f}s +/- {cv_results['mae_std']:.2f}s")
            _log(f"  CV R2:  {cv_results['r2_mean']:.3f} +/- {cv_results['r2_std']:.3f}")

        # Train final model on all data WITH TIME-DECAY SAMPLE WEIGHTS
        # Recent training examples influence the model more than old examples
        model = xgb.XGBRegressor(**model_params)
        model.fit(X, y, sample_weight=sample_weights)

        # Calculate training metrics
        y_pred = model.predict(X)
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)

        _log(f"Final {event} model: {len(X)} records (MAE: {mae:.2f}s, R2: {r2:.3f})")

        # Display feature importance
        if show_feature_importance and verbose:
            display_feature_importance(model, event, feature_cols)

        # Cache the model
        if event == "SB":
            _cached_ml_model_sb = model
            _feature_importance_sb = model.feature_importances_
            _model_cv_metrics_sb = cv_results
        else:  # UH
            _cached_ml_model_uh = model
            _feature_importance_uh = model.feature_importances_
            _model_cv_metrics_uh = cv_results

        models[event] = model

    # Update training data size
    _model_training_data_size = len(validated_df)

    if not models:
        _log("\nERROR: Failed to train any models")
        return None

    # Return both models (use cached if one wasn't trained)
    return {
        "SB": models.get("SB", _cached_ml_model_sb),
        "UH": models.get("UH", _cached_ml_model_uh),
    }


def predict_time_ml(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    wood_df: Optional[pd.DataFrame] = None,
    verbose: bool = False,
) -> Tuple[Optional[float], Optional[str], str]:
    """
    Predict time using event-specific trained ML model (separate SB/UH models).

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (1-10) - not used directly but for consistency
        event_code: Event type (SB or UH)
        results_df: Historical results (optional)
        wood_df: Wood properties (optional)
        verbose: If True, print training progress and metrics

    Returns:
        tuple: (predicted_time, confidence, explanation) or (None, None, error_msg) if error

    Example:
        >>> time, conf, exp = predict_time_ml("John Smith", "WP", 300, 5, "SB")
        >>> if time:
        ...     print(f"ML prediction: {time:.1f}s (confidence: {conf})")
    """
    global _cached_ml_model_sb, _cached_ml_model_uh

    if not ML_AVAILABLE:
        return None, None, "ML libraries not available"

    # Load data if needed
    if results_df is None:
        results_df = load_results_df()

    if results_df is None or results_df.empty:
        return None, None, "No historical data"

    # Standardize results data (shared validation + outlier filtering)
    results_df, _ = standardize_results_data(results_df)

    # Train or get cached models
    models = train_ml_model(
        results_df,
        wood_df,
        force_retrain=False,
        event_code=event_code,
        skip_validation=True,
        verbose=verbose,
        show_feature_importance=verbose,
    )

    if models is None:
        return None, None, "ML model training failed"

    # Select the appropriate model for this event
    event_upper = event_code.upper()
    if event_upper not in models or models[event_upper] is None:
        return None, None, f"No {event_upper} model available"

    model = models[event_upper]

    # Load wood data for properties
    if wood_df is None:
        wood_df = load_wood_data()

    # Get ALL 6 wood properties for maximum accuracy (r=0.621 combined vs 0.523 shear alone)
    wood_janka = 500  # Default
    wood_spec_grav = 0.5  # Default
    wood_shear = 1000  # Default (PSI)
    wood_crush = 4000  # Default (PSI)
    wood_mor = 8000  # Default (PSI)
    wood_moe = 1000000  # Default (PSI)

    if wood_df is not None and not wood_df.empty:
        wood_row = wood_df[wood_df["species"] == species]
        if not wood_row.empty:
            wood_janka = wood_row.iloc[0].get("janka_hard", 500)
            wood_spec_grav = wood_row.iloc[0].get("spec_gravity", 0.5)
            wood_shear = wood_row.iloc[0].get("shear", 1000)
            wood_crush = wood_row.iloc[0].get("crush_strength", 4000)
            wood_mor = wood_row.iloc[0].get("MOR", 8000)
            wood_moe = wood_row.iloc[0].get("MOE", 1000000)

    def _compute_trend_estimate(comp_data: pd.DataFrame) -> Tuple[Optional[float], float, float]:
        if "date" not in comp_data.columns:
            return None, 0.0, 0.0
        if len(comp_data) < ml_config.TREND_MIN_SAMPLES:
            return None, 0.0, 0.0
        dates = pd.to_datetime(comp_data["date"], errors="coerce")
        if dates.isna().all():
            return None, 0.0, 0.0
        x = (dates - dates.min()).dt.days.astype(float)
        y = pd.to_numeric(comp_data["raw_time"], errors="coerce").astype(float)
        valid_mask = np.isfinite(x) & np.isfinite(y)
        x = x[valid_mask]
        y = y[valid_mask]
        if len(x) < 2 or x.nunique() < 2:
            return None, 0.0, 0.0
        try:
            slope, intercept = np.polyfit(x, y, 1)
        except np.linalg.LinAlgError:
            return None, 0.0, 0.0
        y_pred = (slope * x) + intercept
        ss_res = float(((y - y_pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        trend_estimate = float((slope * x.max()) + intercept)
        return trend_estimate, float(slope), float(r2)

    # Calculate competitor average time for this event
    # Use trend-based estimate when reliable; otherwise use time-decay weighting
    comp_data = results_df[(results_df["competitor_name"] == competitor_name) & (results_df["event"] == event_upper)]

    if not comp_data.empty:
        trend_estimate, trend_slope, trend_r2 = _compute_trend_estimate(comp_data)
        use_trend = (
            trend_estimate is not None
            and trend_r2 >= ml_config.TREND_R2_THRESHOLD
            and abs(trend_slope) >= ml_config.TREND_SLOPE_THRESHOLD_SECONDS_PER_DAY
        )
        if use_trend:
            competitor_avg = trend_estimate
        else:
            # Apply time-decay weighting: weight = 0.5^(days_old / 730)
            # This ensures recent performances dominate the average
            if "date" in comp_data.columns:
                weights = comp_data["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))
                competitor_avg = (comp_data["raw_time"] * weights).sum() / weights.sum()
            else:
                competitor_avg = comp_data["raw_time"].mean()

        experience = len(comp_data)
        confidence = "HIGH" if len(comp_data) >= 5 else "MEDIUM"
        trend_feature = trend_slope if use_trend else 0.0
        trend_used = use_trend
    else:
        # Fallback: use all competitor data regardless of event
        comp_all_data = results_df[results_df["competitor_name"] == competitor_name]
        if not comp_all_data.empty:
            # Apply time-decay weighting to cross-event data as well
            if "date" in comp_all_data.columns:
                weights = comp_all_data["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))
                competitor_avg = (comp_all_data["raw_time"] * weights).sum() / weights.sum()
            else:
                competitor_avg = comp_all_data["raw_time"].mean()

            experience = len(comp_all_data)
            confidence = "MEDIUM"
            trend_feature = 0.0
            trend_used = False
        else:
            # New competitor: use event average (time-decay weighted)
            event_data = results_df[results_df["event"] == event_upper]
            if not event_data.empty:
                # Apply time-decay to event baseline as well for consistency
                if "date" in event_data.columns:
                    weights = event_data["date"].apply(lambda d: calculate_performance_weight(d, half_life_days=730))
                    competitor_avg = (event_data["raw_time"] * weights).sum() / weights.sum()
                else:
                    competitor_avg = event_data["raw_time"].mean()

                experience = 1
                confidence = "LOW"
                trend_feature = 0.0
                trend_used = False
            else:
                return None, None, "No reference data for prediction"

    # Prepare full 19-feature vector to match training
    event_encoded = ml_config.EVENT_ENCODING_SB if event_upper == "SB" else ml_config.EVENT_ENCODING_UH

    # Competitor variance and median diameter (event-specific if possible)
    if not comp_data.empty:
        variance_source = comp_data
    elif "comp_all_data" in locals() and not comp_all_data.empty:
        variance_source = comp_all_data
    else:
        variance_source = results_df[results_df["event"] == event_upper]

    competitor_variance = (
        float(pd.to_numeric(variance_source["raw_time"], errors="coerce").std()) if not variance_source.empty else 3.0
    )
    if not np.isfinite(competitor_variance):
        competitor_variance = 3.0

    competitor_median_diameter = (
        float(pd.to_numeric(variance_source["size_mm"], errors="coerce").median())
        if not variance_source.empty
        else float(diameter)
    )
    if not np.isfinite(competitor_median_diameter):
        competitor_median_diameter = float(diameter)

    # Recency score: days since last competition (use most recent gap when possible)
    recency_score = 365.0
    date_source = variance_source if not variance_source.empty else results_df
    if "date" in date_source.columns:
        dates = pd.to_datetime(date_source["date"], errors="coerce").dropna().sort_values()
        if len(dates) >= 2:
            deltas = dates.diff().dt.days.dropna()
            if not deltas.empty:
                recency_score = float(deltas.iloc[-1])
    recency_score = max(0.0, min(1000.0, recency_score))

    # Career phase based on trend slope (match preprocessing thresholds)
    if trend_feature > 0.01:
        career_phase = -1
    elif trend_feature < -0.01:
        career_phase = 1
    else:
        career_phase = 0

    # Seasonal encoding based on most recent date (default to July)
    month = 7
    if "date" in date_source.columns:
        latest_date = pd.to_datetime(date_source["date"], errors="coerce").dropna()
        if not latest_date.empty:
            month = int(latest_date.max().month)
    month_radians = (month - 1) * (2 * np.pi / 12)
    seasonal_month_sin = float(np.sin(month_radians))
    seasonal_month_cos = float(np.cos(month_radians))

    # Quality and derived interactions
    quality = int(quality) if quality is not None else 5
    quality = max(1, min(10, quality))
    wood_quality = float(quality)

    feature_payload = {
        "competitor_avg_time_by_event": competitor_avg,
        "event_encoded": event_encoded,
        "size_mm": float(diameter),
        "wood_janka_hardness": float(wood_janka),
        "wood_spec_gravity": float(wood_spec_grav),
        "wood_shear_strength": float(wood_shear),
        "wood_crush_strength": float(wood_crush),
        "wood_MOR": float(wood_mor),
        "wood_MOE": float(wood_moe),
        "competitor_experience": float(experience),
        "competitor_trend_slope": float(trend_feature),
        "wood_quality": wood_quality,
        "diameter_squared": float(diameter) ** 2,
        "quality_x_diameter": wood_quality * float(diameter),
        "quality_x_hardness": wood_quality * float(wood_janka),
        "experience_x_size": float(experience) * float(diameter),
        "competitor_variance": float(competitor_variance),
        "competitor_median_diameter": float(competitor_median_diameter),
        "recency_score": float(recency_score),
        "career_phase": float(career_phase),
        "seasonal_month_sin": seasonal_month_sin,
        "seasonal_month_cos": seasonal_month_cos,
        "event_x_diameter": float(event_encoded) * float(diameter),
    }

    feature_cols = list(ml_config.FEATURE_NAMES)
    features = pd.DataFrame([feature_payload])[feature_cols]

    # Make prediction using event-specific model
    try:
        base_prediction = model.predict(features)[0]

        # Per-competitor calibration (if enough history and stable residuals)
        calibration_bias = 0.0
        calibration_note = ""
        try:
            features_df = engineer_features_for_ml(results_df, wood_df)
            if features_df is not None:
                comp_rows = features_df[
                    (features_df["competitor_name"] == competitor_name) & (features_df["event"] == event_upper)
                ]
                if len(comp_rows) >= ml_config.CALIBRATION_MIN_SAMPLES:
                    X_comp = comp_rows[list(ml_config.FEATURE_NAMES)]
                    y_comp = comp_rows["raw_time"]
                    preds = model.predict(X_comp)
                    residuals = y_comp - preds
                    residual_std = float(residuals.std())
                    if residual_std <= ml_config.CALIBRATION_MAX_STD_SECONDS:
                        calibration_bias = float(residuals.mean())
                        calibration_note = f", calibrated {calibration_bias:+.1f}s"
        except Exception:
            calibration_bias = 0.0

        base_prediction = base_prediction + calibration_bias

        # Apply WOOD QUALITY ADJUSTMENT
        # Quality scale: 1-10, where 5 is average
        # Lower quality (1-4) = softer wood = faster times (negative adjustment)
        # Higher quality (6-10) = harder wood = slower times (positive adjustment)
        # Adjustment: ±2% per quality point from average
        quality = int(quality) if quality is not None else 5
        quality = max(1, min(10, quality))
        quality_offset = quality - 5  # Range: -5 to +5
        quality_factor = 1.0 + (quality_offset * 0.02)  # -10% to +10%

        predicted_time = base_prediction * quality_factor

        # Sanity check: ensure prediction is reasonable
        if predicted_time < 5 or predicted_time > 300:
            return None, None, f"ML prediction out of range ({predicted_time:.1f}s)"

        # Build explanation with quality adjustment info
        explanation = f"{event_upper} ML model ({_model_training_data_size} training records){calibration_note}"
        if trend_used:
            explanation += ", trend-based avg"

        if quality != 5:
            adjustment_pct = (quality_factor - 1.0) * 100
            if quality < 5:
                explanation += f", quality {quality}/10 (softer, {adjustment_pct:+.0f}%)"
            else:
                explanation += f", quality {quality}/10 (harder, {adjustment_pct:+.0f}%)"

        # Calibrate confidence using model CV MAE when available
        cv_metrics = _model_cv_metrics_sb if event_upper == "SB" else _model_cv_metrics_uh
        if cv_metrics and "mae_mean" in cv_metrics:
            mae = cv_metrics["mae_mean"]
            if mae > ml_config.ML_MAE_MEDIUM_CONFIDENCE:
                confidence = "LOW"
            elif mae > ml_config.ML_MAE_HIGH_CONFIDENCE and confidence == "HIGH":
                confidence = "MEDIUM"

        return predicted_time, confidence, explanation

    except Exception as e:
        return None, None, f"ML prediction error: {str(e)}"


def get_model_cv_metrics(event_code: str) -> Optional[dict]:
    """Return cached CV metrics for the requested event."""
    event_upper = event_code.upper()
    if event_upper == "SB":
        return _model_cv_metrics_sb
    if event_upper == "UH":
        return _model_cv_metrics_uh
    return None
