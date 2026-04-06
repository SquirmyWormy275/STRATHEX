"""Feature engineering and preprocessing for machine learning models."""

import os

# Import config
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import baseline_v2_config, data_req, ml_config

# Import local modules
from woodchopping.data.excel_io import load_wood_data


def engineer_features_for_ml(
    results_df: pd.DataFrame, wood_df: Optional[pd.DataFrame] = None
) -> Optional[pd.DataFrame]:
    """
    Engineer 23 features for ML model from historical results (ALL 6 wood properties).

    Data analysis showed ALL 6 wood properties combined: r=0.621 vs shear alone r=0.523

    Features created:
    1. competitor_avg_time_by_event - Historical average for this event (PRIMARY)
    2. event_encoded - Binary encoding (SB=0, UH=1)
    3. size_mm - Block diameter (already present)
    4. wood_janka_hardness - Joined from wood properties
    5. wood_spec_gravity - Joined from wood properties
    6. wood_shear_strength - Shear strength PSI (BEST single predictor r=0.527)
    7. wood_crush_strength - Compression strength PSI (r=0.447)
    8. wood_MOR - Modulus of Rupture PSI (bending strength)
    9. wood_MOE - Modulus of Elasticity PSI (stiffness)
    10. competitor_experience - Count of past events
    11. competitor_trend_slope - Performance trajectory (seconds/day)
    12. wood_quality - Wood firmness/hardness (0-10 scale) - CRITICAL FEATURE
    13. diameter_squared - Non-linear size effect
    14. quality_x_diameter - Interaction: soft wood easier on large blocks
    15. quality_x_hardness - Interaction: quality matters more for hard wood
    16. experience_x_size - Interaction: novices struggle with large blocks
    17. competitor_variance - Historical std_dev (consistency)
    18. competitor_median_diameter - Selection bias proxy
    19. recency_score - Days since last competition
    20. career_phase - Rising (1), peak (0), declining (-1)
    21. seasonal_month_sin - Cyclical month encoding (sin component)
    22. seasonal_month_cos - Cyclical month encoding (cos component)
    23. event_x_diameter - Interaction: UH vs SB differ in diameter scaling

    Args:
        results_df: DataFrame with historical results
        wood_df: DataFrame with wood properties (optional, will load if not provided)

    Returns:
        DataFrame with engineered features ready for training/prediction, or None if error
    """
    if results_df is None or results_df.empty:
        return None

    # Load wood data if not provided
    if wood_df is None:
        wood_df = load_wood_data()

    # Create a copy to avoid modifying original
    df = results_df.copy()

    # Ensure required columns exist
    required_cols = ["competitor_name", "event", "raw_time", "size_mm", "species"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Warning: Missing required columns for ML: {missing}")
        return None

    # Remove invalid records
    df = df[df["raw_time"] > 0].copy()
    df = df[df["size_mm"] > 0].copy()

    if df.empty:
        return None

    # Feature 1: Event type encoding (SB=0, UH=1)
    df["event_encoded"] = df["event"].apply(
        lambda x: ml_config.EVENT_ENCODING_SB if str(x).upper() == "SB" else ml_config.EVENT_ENCODING_UH
    )

    # Feature 2: Competitor average time by event (trend-aware when reliable)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        def _trend_stats(group: pd.DataFrame) -> pd.Series:
            sample_count = len(group)
            if sample_count < ml_config.TREND_MIN_SAMPLES:
                return pd.Series(
                    {
                        "trend_slope": 0.0,
                        "trend_r2": 0.0,
                        "trend_estimate": group["raw_time"].mean(),
                        "trend_samples": sample_count,
                    }
                )

            dates = group["date"]
            if dates.isna().all():
                return pd.Series(
                    {
                        "trend_slope": 0.0,
                        "trend_r2": 0.0,
                        "trend_estimate": group["raw_time"].mean(),
                        "trend_samples": sample_count,
                    }
                )

            x = (dates - dates.min()).dt.days.astype(float)
            y = pd.to_numeric(group["raw_time"], errors="coerce").astype(float)
            valid_mask = np.isfinite(x) & np.isfinite(y)
            x = x[valid_mask]
            y = y[valid_mask]
            if len(x) < 2 or x.nunique() < 2:
                return pd.Series(
                    {
                        "trend_slope": 0.0,
                        "trend_r2": 0.0,
                        "trend_estimate": float(pd.to_numeric(group["raw_time"], errors="coerce").mean()),
                        "trend_samples": sample_count,
                    }
                )

            try:
                slope, intercept = np.polyfit(x, y, 1)
            except np.linalg.LinAlgError:
                return pd.Series(
                    {
                        "trend_slope": 0.0,
                        "trend_r2": 0.0,
                        "trend_estimate": float(pd.to_numeric(group["raw_time"], errors="coerce").mean()),
                        "trend_samples": sample_count,
                    }
                )
            y_pred = (slope * x) + intercept
            ss_res = float(((y - y_pred) ** 2).sum())
            ss_tot = float(((y - y.mean()) ** 2).sum())
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            trend_estimate = float((slope * x.max()) + intercept)

            return pd.Series(
                {
                    "trend_slope": float(slope),
                    "trend_r2": float(r2),
                    "trend_estimate": trend_estimate,
                    "trend_samples": sample_count,
                }
            )

        trend_stats = df.groupby(["competitor_name", "event"]).apply(_trend_stats).reset_index()

        df = df.merge(trend_stats, on=["competitor_name", "event"], how="left")

        competitor_avg = df.groupby(["competitor_name", "event"])["raw_time"].transform("mean")
        use_trend = (
            (df["trend_samples"] >= ml_config.TREND_MIN_SAMPLES)
            & (df["trend_r2"] >= ml_config.TREND_R2_THRESHOLD)
            & (df["trend_slope"].abs() >= ml_config.TREND_SLOPE_THRESHOLD_SECONDS_PER_DAY)
        )
        df["competitor_avg_time_by_event"] = np.where(use_trend, df["trend_estimate"], competitor_avg)
        df["competitor_trend_slope"] = df["trend_slope"].fillna(0.0)
    else:
        competitor_avg = df.groupby(["competitor_name", "event"])["raw_time"].transform("mean")
        df["competitor_avg_time_by_event"] = competitor_avg
        df["competitor_trend_slope"] = 0.0

    # Feature 3: Competitor experience (count of past events)
    df["competitor_experience"] = df.groupby("competitor_name").cumcount() + 1

    # Feature 4: Size (already present as size_mm)

    # Features 5-9: Join ALL 6 wood properties for maximum accuracy (r=0.621 combined)
    # Data analysis: Shear (r=0.527), Crush (r=0.447), Janka (r=0.414), MOE (r=0.398)
    if not wood_df.empty and "speciesID" in wood_df.columns:
        # Create species code mapping - use speciesID to match with Results sheet species codes
        wood_cols = [
            "speciesID",
            "janka_hard",
            "spec_gravity",
            "shear",
            "crush_strength",
            "MOR",
            "MOE",
        ]
        available_cols = [c for c in wood_cols if c in wood_df.columns]
        wood_properties = wood_df[available_cols].copy()

        wood_properties = wood_properties.rename(
            columns={
                "speciesID": "species",
                "janka_hard": "wood_janka_hardness",
                "spec_gravity": "wood_spec_gravity",
                "shear": "wood_shear_strength",
                "crush_strength": "wood_crush_strength",
                "MOR": "wood_MOR",
                "MOE": "wood_MOE",
            }
        )

        # Join wood properties with results
        df = df.merge(wood_properties, on="species", how="left")

        # Fill missing wood properties with median values (or defaults)
        wood_feature_defaults = {
            "wood_janka_hardness": ml_config.DEFAULT_JANKA_HARDNESS,
            "wood_spec_gravity": ml_config.DEFAULT_SPECIFIC_GRAVITY,
            "wood_shear_strength": 1000,  # Default shear PSI
            "wood_crush_strength": 4000,  # Default crush PSI
            "wood_MOR": 8000,  # Default modulus of rupture PSI
            "wood_MOE": 1000000,  # Default modulus of elasticity PSI
        }

        for feature, default_val in wood_feature_defaults.items():
            if feature in df.columns:
                median_val = df[feature].median()
                df[feature] = df[feature].fillna(median_val if pd.notna(median_val) else default_val)
            else:
                df[feature] = default_val
    else:
        # If wood data not available, use default values
        df["wood_janka_hardness"] = ml_config.DEFAULT_JANKA_HARDNESS
        df["wood_spec_gravity"] = ml_config.DEFAULT_SPECIFIC_GRAVITY
        df["wood_shear_strength"] = 1000
        df["wood_crush_strength"] = 4000
        df["wood_MOR"] = 8000
        df["wood_MOE"] = 1000000

    # ============================================================================
    # NEW FEATURES (8-19): Enhanced Feature Engineering for Stacking Ensemble
    # ============================================================================

    # Feature 8: Wood quality (0-10 firmness scale) - CRITICAL MISSING FEATURE
    # Quality has 12-15% effect on times, currently only used by Baseline V2 and LLM
    if "quality" in df.columns:
        df["wood_quality"] = pd.to_numeric(df["quality"], errors="coerce").fillna(5.0)
        # Clamp to valid range [0, 10]
        df["wood_quality"] = df["wood_quality"].clip(0, 10)
    else:
        # Default to average quality if column missing (backward compatibility)
        df["wood_quality"] = 5.0

    # Feature 9: Diameter squared - Capture non-linear size effects
    df["diameter_squared"] = df["size_mm"] ** 2

    # Feature 10: Quality x Diameter interaction
    # Rationale: Soft wood on large blocks saves MORE time than soft wood on small blocks
    df["quality_x_diameter"] = df["wood_quality"] * df["size_mm"]

    # Feature 11: Quality x Hardness interaction
    # Rationale: Quality variation matters MORE for inherently hard species
    df["quality_x_hardness"] = df["wood_quality"] * df["wood_janka_hardness"]

    # Feature 12: Experience x Size interaction
    # Rationale: Novice competitors struggle disproportionately with large blocks
    df["experience_x_size"] = df["competitor_experience"] * df["size_mm"]

    # Feature 13: Competitor variance (consistency) - Historical std_dev
    # Captures how consistent each competitor is (low std = very consistent)
    competitor_variance = df.groupby(["competitor_name", "event"])["raw_time"].transform("std").fillna(3.0)
    df["competitor_variance"] = competitor_variance

    # Feature 14: Competitor median diameter - Selection bias proxy
    # Elite competitors tend to choose larger diameters (negative correlation detected: -0.36 to -0.38)
    competitor_median_diameter = df.groupby(["competitor_name", "event"])["size_mm"].transform("median")
    df["competitor_median_diameter"] = competitor_median_diameter.fillna(df["size_mm"])

    # Feature 15: Recency score - Days since last competition
    # Captures momentum vs rust effects
    if "date" in df.columns and df["date"].notna().any():
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Sort by date to calculate days since last comp
        df = df.sort_values(["competitor_name", "event", "date"])
        df["days_since_last"] = df.groupby(["competitor_name", "event"])["date"].diff().dt.days
        # First competition for each competitor has NaN - fill with median
        df["recency_score"] = df["days_since_last"].fillna(df["days_since_last"].median())
        # Cap at 1000 days to prevent extreme values
        df["recency_score"] = df["recency_score"].clip(0, 1000)
    else:
        # No date data - use neutral value
        df["recency_score"] = 365.0

    # Feature 16: Career phase - Rising/peak/declining based on trend
    # Already computed in trend_slope logic, but now create categorical flag
    if "competitor_trend_slope" in df.columns:
        # Rising = positive slope (getting faster/better)
        # Peak = flat slope (stable performance)
        # Declining = negative slope (getting slower/worse)
        def _career_phase(slope):
            if pd.isna(slope):
                return 0  # Unknown/peak
            if slope > 0.01:  # Getting slower (declining in woodchopping = higher times)
                return -1
            elif slope < -0.01:  # Getting faster (improving)
                return 1
            else:
                return 0  # Stable/peak

        df["career_phase"] = df["competitor_trend_slope"].apply(_career_phase)
    else:
        df["career_phase"] = 0

    # Features 17-18: Seasonal encoding (sin/cos for cyclical patterns)
    # American woodchopping season: April-September
    # Peak season: June-August, Early season: April-May, Late season: September
    if "date" in df.columns and df["date"].notna().any():
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Extract month and convert to radians (1-12 -> 0-2?)
        month = df["date"].dt.month.fillna(7)  # Default to July (mid-season)
        month_radians = (month - 1) * (2 * np.pi / 12)
        df["seasonal_month_sin"] = np.sin(month_radians)
        df["seasonal_month_cos"] = np.cos(month_radians)
    else:
        # No date data - use mid-season defaults (July = month 7)
        month_radians = (7 - 1) * (2 * np.pi / 12)
        df["seasonal_month_sin"] = np.sin(month_radians)
        df["seasonal_month_cos"] = np.cos(month_radians)

    # Feature 19: Event x Diameter interaction
    # Rationale: UH (Underhand) and SB (Standing Block) scale differently with diameter
    df["event_x_diameter"] = df["event_encoded"] * df["size_mm"]

    return df


# ============================================================================
# PHASE 1: HYBRID BASELINE V2 PREPROCESSING FUNCTIONS
# ============================================================================


def load_and_clean_results(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize and validate Results sheet for Baseline V2 hybrid model.

    Standardizes column names and data types for consistent processing:
    - Time -> raw_time (seconds)
    - Diameter -> size_mm (millimeters)
    - Species -> species (species code)
    - Event -> event (uppercase SB/UH)
    - Date -> date (pandas datetime)

    Args:
        results_df: Raw results DataFrame from Excel

    Returns:
        Cleaned DataFrame with standardized columns
    """
    if results_df is None or results_df.empty:
        return results_df

    # Create a copy to avoid modifying original
    df = results_df.copy()

    # Standardize column names (case-insensitive mapping)
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if "time" in col_lower and "raw" not in col_lower:
            column_mapping[col] = "raw_time"
        elif "diameter" in col_lower:
            column_mapping[col] = "size_mm"
        elif col_lower == "species":
            column_mapping[col] = "species"
        elif col_lower == "event":
            column_mapping[col] = "event"
        elif "date" in col_lower:
            column_mapping[col] = "date"
        elif "quality" in col_lower:
            column_mapping[col] = "quality"

    # Only rename columns that need renaming
    if column_mapping:
        df = df.rename(columns=column_mapping)

    # Ensure event is uppercase
    if "event" in df.columns:
        df["event"] = df["event"].str.upper()

    # Convert date to datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Ensure numeric types
    if "raw_time" in df.columns:
        df["raw_time"] = pd.to_numeric(df["raw_time"], errors="coerce")
    if "size_mm" in df.columns:
        df["size_mm"] = pd.to_numeric(df["size_mm"], errors="coerce")
    if "quality" in df.columns:
        df["quality"] = pd.to_numeric(df["quality"], errors="coerce")

    # Remove invalid records (use configured thresholds)
    if "raw_time" in df.columns:
        df = df[
            (df["raw_time"] > data_req.MIN_VALID_TIME_SECONDS) & (df["raw_time"] <= data_req.MAX_VALID_TIME_SECONDS)
        ]
    if "size_mm" in df.columns:
        df = df[(df["size_mm"] >= data_req.MIN_DIAMETER_MM) & (df["size_mm"] <= data_req.MAX_DIAMETER_MM)]

    return df


def fit_wood_hardness_index(results_df: pd.DataFrame, wood_df: pd.DataFrame) -> dict:
    """
    Learn 6-property composite wood hardness index from actual performance data.

    Uses weighted regression to find optimal weights for:
    - Janka hardness
    - Specific gravity
    - Crush strength
    - Shear strength
    - MOR (Modulus of Rupture)
    - MOE (Modulus of Elasticity)

    The weights are learned from historical performance data, addressing issues
    like the "Hybrid Poplar paradox" where Janka alone doesn't predict cutting time.

    Args:
        results_df: Historical results (cleaned via load_and_clean_results)
        wood_df: Wood properties DataFrame

    Returns:
        Dictionary mapping speciesID to composite hardness index
    """
    if results_df is None or results_df.empty or wood_df is None or wood_df.empty:
        return {}

    df = results_df.copy()
    if "raw_time" not in df.columns or "size_mm" not in df.columns:
        df = load_and_clean_results(df)

    required_cols = {"competitor_name", "event", "raw_time", "size_mm", "species"}
    if not required_cols.issubset(df.columns):
        return {}

    df = df[
        (df["raw_time"] > data_req.MIN_VALID_TIME_SECONDS)
        & (df["raw_time"] <= data_req.MAX_VALID_TIME_SECONDS)
        & (df["size_mm"] >= data_req.MIN_DIAMETER_MM)
        & (df["size_mm"] <= data_req.MAX_DIAMETER_MM)
    ].copy()

    def _janka_scale() -> float:
        median_janka = pd.to_numeric(wood_df.get("janka_hard"), errors="coerce").median()
        if pd.isna(median_janka) or median_janka <= 0:
            return 1.0
        return float(median_janka)

    if len(df) < baseline_v2_config.MIN_TOTAL_SAMPLES_FOR_INDEX:
        print("[Baseline V2] Insufficient data for hardness index regression. Using Janka proxy.")
        janka_scale = _janka_scale()
        return {
            str(row["speciesID"]).strip(): float(row["janka_hard"]) / janka_scale
            for _, row in wood_df.iterrows()
            if pd.notna(row.get("speciesID")) and pd.notna(row.get("janka_hard"))
        }

    wood_cols = ["janka_hard", "spec_gravity", "crush_strength", "shear", "MOR", "MOE"]
    available_features = [c for c in wood_cols if c in wood_df.columns and wood_df[c].notna().sum() > 0]
    if len(available_features) < 2:
        print("[Baseline V2] Insufficient wood property data. Using Janka proxy.")
        janka_scale = _janka_scale()
        return {
            str(row["speciesID"]).strip(): float(row["janka_hard"]) / janka_scale
            for _, row in wood_df.iterrows()
            if pd.notna(row.get("speciesID")) and pd.notna(row.get("janka_hard"))
        }

    df["log_time"] = np.log(df["raw_time"])

    def _fit_diameter_curve(event_df: pd.DataFrame) -> np.ndarray:
        if len(event_df) < baseline_v2_config.DIAMETER_CURVE_MIN_SAMPLES:
            return np.array([0.0, 0.0, 0.0])
        x = event_df["size_mm"].astype(float).values
        y = event_df["log_time"].astype(float).values
        X = np.column_stack([np.ones(len(x)), x, x**2])
        try:
            return np.linalg.lstsq(X, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            return np.array([0.0, 0.0, 0.0])

    curves = {}
    for event in df["event"].unique():
        event_df = df[df["event"] == event]
        curves[event] = _fit_diameter_curve(event_df)

    def _predict_curve(row):
        coeffs = curves.get(row["event"])
        if coeffs is None:
            coeffs = np.array([0.0, 0.0, 0.0])
        return coeffs[0] + coeffs[1] * row["size_mm"] + coeffs[2] * (row["size_mm"] ** 2)

    df["diameter_effect"] = df.apply(_predict_curve, axis=1)
    df["residual"] = df["log_time"] - df["diameter_effect"]

    comp_event_mean = df.groupby(["competitor_name", "event"])["residual"].transform("mean")
    df["residual_adj"] = df["residual"] - comp_event_mean

    species_stats = df.groupby("species")["residual_adj"].agg(["mean", "count"]).reset_index()

    species_stats = species_stats[species_stats["count"] >= baseline_v2_config.MIN_SPECIES_SAMPLES]

    if species_stats["species"].nunique() < baseline_v2_config.MIN_SPECIES_VARIETY:
        print("[Baseline V2] Insufficient species variety. Using Janka proxy.")
        janka_scale = _janka_scale()
        return {
            str(row["speciesID"]).strip(): float(row["janka_hard"]) / janka_scale
            for _, row in wood_df.iterrows()
            if pd.notna(row.get("speciesID")) and pd.notna(row.get("janka_hard"))
        }

    wood_map = wood_df.copy()
    wood_map["speciesID"] = wood_map["speciesID"].astype(str).str.strip()

    species_features = []
    species_targets = []
    species_weights = []
    species_ids = []

    for _, row in species_stats.iterrows():
        species_id = str(row["species"]).strip()
        wood_row = wood_map[wood_map["speciesID"] == species_id]
        if wood_row.empty:
            continue
        feature_row = []
        for feat in available_features:
            val = wood_row.iloc[0].get(feat)
            if pd.isna(val):
                val = wood_map[feat].median()
            feature_row.append(float(val))
        species_features.append(feature_row)
        species_targets.append(float(row["mean"]))
        species_weights.append(float(row["count"]))
        species_ids.append(species_id)

    if len(species_features) < baseline_v2_config.MIN_SPECIES_VARIETY:
        print("[Baseline V2] Insufficient species variety after merging. Using Janka proxy.")
        janka_scale = _janka_scale()
        return {
            str(row["speciesID"]).strip(): float(row["janka_hard"]) / janka_scale
            for _, row in wood_df.iterrows()
            if pd.notna(row.get("speciesID")) and pd.notna(row.get("janka_hard"))
        }

    X = np.array(species_features, dtype=float)
    y = np.array(species_targets, dtype=float)
    w = np.array(species_weights, dtype=float)

    mins = X.min(axis=0)
    maxs = X.max(axis=0)
    denom = np.where(maxs > mins, (maxs - mins), 1.0)
    X_norm = (X - mins) / denom

    try:
        sqrt_w = np.sqrt(w)
        Xw = X_norm * sqrt_w[:, None]
        yw = y * sqrt_w
        coeffs = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    except np.linalg.LinAlgError:
        print("[Baseline V2] Regression failed. Using Janka proxy.")
        janka_scale = _janka_scale()
        return {
            str(row["speciesID"]).strip(): float(row["janka_hard"]) / janka_scale
            for _, row in wood_df.iterrows()
            if pd.notna(row.get("speciesID")) and pd.notna(row.get("janka_hard"))
        }

    # Compute composite index for each species using regression estimates
    hardness_index = {}
    all_preds = []
    for _, row in wood_map.iterrows():
        feature_values = []
        for feat in available_features:
            val = row.get(feat)
            if pd.isna(val):
                val = wood_map[feat].median()
            feature_values.append(float(val))
        feature_values = np.array(feature_values, dtype=float)
        feature_norm = (feature_values - mins) / denom
        pred = float(np.dot(feature_norm, coeffs))
        all_preds.append(pred)
        hardness_index[str(row["speciesID"]).strip()] = pred

    mean_pred = float(np.mean(all_preds)) if all_preds else 0.0
    for key in list(hardness_index.keys()):
        # Convert residual in log-space to multiplicative factor and center at 1.0
        hardness_index[key] = float(np.exp(hardness_index[key] - mean_pred))

    print(
        f"[Baseline V2] Learned wood hardness index from {len(available_features)} properties "
        f"using {len(species_ids)} species"
    )

    return hardness_index


def calculate_adaptive_half_lives(results_df: pd.DataFrame) -> dict:
    """
    Assign competitor-specific time-decay half-lives based on activity level.

    Active competitors (enough recent results): shorter half-life (faster decay)
    Moderate activity: standard half-life
    Inactive competitors: longer half-life (preserve old data longer)

    Rationale: Active competitors' performance changes rapidly; inactive competitors
    are more stable over time.

    Args:
        results_df: Historical results with 'date' column

    Returns:
        Dictionary mapping competitor_name to half-life in days
    """
    half_lives = {}

    if "date" not in results_df.columns or results_df["date"].isna().all():
        print("[Baseline V2] No date data available. Using standard half-life for all competitors.")
        # Default to standard half-life
        for competitor in results_df["competitor_name"].unique():
            half_lives[competitor] = baseline_v2_config.HALF_LIFE_MODERATE_DAYS
        return half_lives

    # Calculate reference date (most recent date in dataset)
    max_date = results_df["date"].max()
    if pd.isna(max_date):
        for competitor in results_df["competitor_name"].unique():
            half_lives[competitor] = baseline_v2_config.HALF_LIFE_MODERATE_DAYS
        return half_lives

    # Define activity window
    activity_window_days = baseline_v2_config.ACTIVITY_WINDOW_DAYS
    cutoff_date = max_date - pd.Timedelta(days=activity_window_days)

    for competitor in results_df["competitor_name"].unique():
        competitor_data = results_df[results_df["competitor_name"] == competitor]

        # Count recent results (within last 2 years)
        recent_results = competitor_data[competitor_data["date"] >= cutoff_date]
        recent_count = len(recent_results)

        # Assign half-life based on activity level
        if recent_count >= baseline_v2_config.ACTIVE_MIN_RESULTS:
            half_lives[competitor] = baseline_v2_config.HALF_LIFE_ACTIVE_DAYS
        elif recent_count >= baseline_v2_config.MODERATE_MIN_RESULTS:
            half_lives[competitor] = baseline_v2_config.HALF_LIFE_MODERATE_DAYS
        else:
            half_lives[competitor] = baseline_v2_config.HALF_LIFE_INACTIVE_DAYS

    # Activity level distribution
    active_count = sum(1 for hl in half_lives.values() if hl == baseline_v2_config.HALF_LIFE_ACTIVE_DAYS)
    moderate_count = sum(1 for hl in half_lives.values() if hl == baseline_v2_config.HALF_LIFE_MODERATE_DAYS)
    inactive_count = sum(1 for hl in half_lives.values() if hl == baseline_v2_config.HALF_LIFE_INACTIVE_DAYS)

    print(
        f"[Baseline V2] Adaptive half-lives: {active_count} active "
        f"({baseline_v2_config.HALF_LIFE_ACTIVE_DAYS}d), {moderate_count} moderate "
        f"({baseline_v2_config.HALF_LIFE_MODERATE_DAYS}d), {inactive_count} inactive "
        f"({baseline_v2_config.HALF_LIFE_INACTIVE_DAYS}d)"
    )

    return half_lives
