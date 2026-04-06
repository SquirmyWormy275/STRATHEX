"""Data validation and cleaning functions for woodchopping competition results."""

import os

# Import config
import sys
from typing import List, Optional, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import data_req, events


def validate_results_data(results_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Validate and clean historical results data.

    Performs comprehensive validation including:
    - Required columns check
    - Time range validation (0-300s)
    - Diameter validation (150-500mm)
    - Missing data removal
    - Event code validation (SB/UH only)
    - Statistical outlier detection (3x IQR method)

    Args:
        results_df: Raw results DataFrame

    Returns:
        Tuple of (cleaned_df, warnings_list). Returns (None, warnings) if validation fails.
    """
    warnings: List[str] = []

    if results_df is None or results_df.empty:
        return None, ["No data to validate"]

    df = results_df.copy()
    initial_count = len(df)

    # Check for required columns
    required_cols = ["competitor_name", "event", "raw_time", "size_mm", "species"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        warnings.append(f"Missing columns: {missing_cols}")
        return None, warnings

    # Coerce quality to numeric if present (non-numeric becomes NaN)
    if "quality" in df.columns:
        df["quality"] = pd.to_numeric(df["quality"], errors="coerce")

    # Coerce time and size to numeric to prevent comparison errors
    df["raw_time"] = pd.to_numeric(df["raw_time"], errors="coerce")
    df["size_mm"] = pd.to_numeric(df["size_mm"], errors="coerce")

    # Remove rows with missing core numeric fields
    missing_numeric = df[df["raw_time"].isna() | df["size_mm"].isna()]
    if not missing_numeric.empty:
        warnings.append(f"Removed {len(missing_numeric)} records with non-numeric time/diameter")
        df = df[df["raw_time"].notna() & df["size_mm"].notna()]

    # Remove invalid times (use config constants)
    invalid_times = df[
        (df["raw_time"] <= data_req.MIN_VALID_TIME_SECONDS) | (df["raw_time"] > data_req.MAX_VALID_TIME_SECONDS)
    ]
    if not invalid_times.empty:
        warnings.append(
            f"Removed {len(invalid_times)} records with impossible times "
            f"(<{data_req.MIN_VALID_TIME_SECONDS}s or >{data_req.MAX_VALID_TIME_SECONDS}s)"
        )
        df = df[
            (df["raw_time"] > data_req.MIN_VALID_TIME_SECONDS) & (df["raw_time"] <= data_req.MAX_VALID_TIME_SECONDS)
        ]

    # Remove invalid sizes (use config constants)
    invalid_sizes = df[(df["size_mm"] < data_req.MIN_DIAMETER_MM) | (df["size_mm"] > data_req.MAX_DIAMETER_MM)]
    if not invalid_sizes.empty:
        warnings.append(
            f"Removed {len(invalid_sizes)} records with invalid diameters "
            f"(<{data_req.MIN_DIAMETER_MM}mm or >{data_req.MAX_DIAMETER_MM}mm)"
        )
        df = df[(df["size_mm"] >= data_req.MIN_DIAMETER_MM) & (df["size_mm"] <= data_req.MAX_DIAMETER_MM)]

    # Check for missing competitor names
    missing_names = df[df["competitor_name"].isna() | (df["competitor_name"] == "")]
    if not missing_names.empty:
        warnings.append(f"Removed {len(missing_names)} records with missing competitor names")
        df = df[df["competitor_name"].notna() & (df["competitor_name"] != "")]

    # Normalize event codes before validation (e.g., "sb" -> "SB")
    if "event" in df.columns:
        df["event"] = df["event"].astype(str).str.strip().str.upper()

    # Check for invalid event codes (use config constants)
    invalid_events = df[~df["event"].isin(events.VALID_EVENTS)]
    if not invalid_events.empty:
        warnings.append(
            f"Removed {len(invalid_events)} records with invalid event codes "
            f"(must be {' or '.join(events.VALID_EVENTS)})"
        )
        df = df[df["event"].isin(events.VALID_EVENTS)]

    # Detect statistical outliers using IQR method (event + size bins when possible)
    outliers_removed = 0
    if "size_mm" in df.columns:
        df["size_bin"] = (df["size_mm"] / 25.0).round() * 25.0

    for event in events.VALID_EVENTS:
        event_df = df[df["event"] == event]
        if len(event_df) <= 10:
            continue

        # Event-level fallback bounds
        Q1 = event_df["raw_time"].quantile(0.25)
        Q3 = event_df["raw_time"].quantile(0.75)
        IQR = Q3 - Q1
        event_lower = Q1 - data_req.OUTLIER_IQR_MULTIPLIER * IQR
        event_upper = Q3 + data_req.OUTLIER_IQR_MULTIPLIER * IQR

        if "size_bin" in df.columns:
            for _, group in event_df.groupby("size_bin"):
                if len(group) >= 10:
                    gq1 = group["raw_time"].quantile(0.25)
                    gq3 = group["raw_time"].quantile(0.75)
                    giqr = gq3 - gq1
                    lower = gq1 - data_req.OUTLIER_IQR_MULTIPLIER * giqr
                    upper = gq3 + data_req.OUTLIER_IQR_MULTIPLIER * giqr
                else:
                    lower = event_lower
                    upper = event_upper

                outliers = group[(group["raw_time"] < lower) | (group["raw_time"] > upper)]
                if not outliers.empty:
                    outliers_removed += len(outliers)
                    df = df.drop(index=outliers.index)
        else:
            outliers = event_df[(event_df["raw_time"] < event_lower) | (event_df["raw_time"] > event_upper)]
            if not outliers.empty:
                outliers_removed += len(outliers)
                df = df.drop(index=outliers.index)

    if outliers_removed > 0:
        warnings.append(
            f"Removed {outliers_removed} statistical outliers (>{data_req.OUTLIER_IQR_MULTIPLIER}x IQR from median)"
        )

    if "size_bin" in df.columns:
        df = df.drop(columns=["size_bin"])

    final_count = len(df)
    if final_count < initial_count:
        warnings.append(
            f"Data cleaned: {initial_count} -> {final_count} records ({initial_count - final_count} removed)"
        )

    if final_count < data_req.MIN_ML_TRAINING_RECORDS_TOTAL:
        warnings.append(
            f"Warning: Only {final_count} valid records remaining "
            f"(need {data_req.MIN_ML_TRAINING_RECORDS_TOTAL}+ for ML training)"
        )

    return df, warnings


def standardize_results_data(results_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], List[str]]:
    """
    Standardize results data using the shared validation and outlier filtering rules.

    This is a lightweight wrapper around validate_results_data() that:
    - Returns the original DataFrame if validation fails (to avoid hard stops)
    - Tags validated DataFrames to prevent repeated work

    Args:
        results_df: Raw results DataFrame

    Returns:
        Tuple of (cleaned_df_or_original, warnings_list)
    """
    if results_df is None or results_df.empty:
        return results_df, ["No data to validate"]

    # Avoid re-validating the same DataFrame repeatedly
    if getattr(results_df, "attrs", {}).get("validated", False):
        return results_df, []

    cleaned_df, warnings = validate_results_data(results_df)

    if cleaned_df is None or cleaned_df.empty:
        return results_df, warnings

    cleaned_df.attrs["validated"] = True
    return cleaned_df, warnings


def validate_heat_data(heat_assignment_df, wood_selection):
    """
    Validate that heat assignment and wood selection are ready for handicap calculation.

    Args:
        heat_assignment_df: DataFrame of competitors in the heat
        wood_selection: Dictionary with wood characteristics

    Returns:
        bool: True if valid, False if missing required data

    Example:
        >>> if validate_heat_data(heat_df, wood_dict):
        ...     calculate_handicaps(...)
    """
    if heat_assignment_df is None or heat_assignment_df.empty:
        print("\nNo competitors in heat assignment. Use Competitor Menu -> Select Competitors for Heat.")
        return False

    if not wood_selection.get("species") or not wood_selection.get("size_mm"):
        print("\nWood selection incomplete. Use Wood Menu to set species and size.")
        return False

    if not wood_selection.get("event"):
        print("\nEvent not selected. Use Wood Menu -> Select event (SB/UH) or Main Menu option 3.")
        return False

    return True


# ===== SPARSE DATA VALIDATION =====
# Based on statistical analysis of 1003 historical results:
# - N < 3: Insufficient for basic statistics (BLOCK)
# - N < 10: Low confidence predictions (WARN)
# - N >= 10: Moderate to high confidence

ABSOLUTE_MINIMUM_RESULTS = 3  # Hard block - cannot make prediction
RECOMMENDED_MINIMUM_RESULTS = 10  # Soft warning - lower confidence


def get_competitor_result_count(results_df: pd.DataFrame, competitor_name: str, event: str = None) -> int:
    """
    Count how many historical results a competitor has.

    Args:
        results_df: Historical results DataFrame
        competitor_name: Competitor name to check
        event: Optional event filter (e.g., 'UH', 'SB'). If None, counts all events.

    Returns:
        int: Number of historical results
    """
    if results_df is None or results_df.empty:
        return 0

    # Filter by competitor name (case-insensitive)
    comp_data = results_df[results_df["competitor_name"].str.lower() == competitor_name.lower()]

    # Filter by event if specified
    if event:
        event = event.upper()
        comp_data = comp_data[comp_data["event"] == event]

    return len(comp_data)


def get_data_confidence_level(result_count: int) -> str:
    """
    Determine confidence level based on result count.

    Based on empirical analysis:
    - N=3: 8-12s prediction error
    - N=10: 2-4s prediction error

    Args:
        result_count: Number of historical results

    Returns:
        str: Confidence level ('BLOCKED', 'LOW', 'MEDIUM', 'HIGH')
    """
    if result_count < ABSOLUTE_MINIMUM_RESULTS:
        return "BLOCKED"
    elif result_count < RECOMMENDED_MINIMUM_RESULTS:
        return "LOW"
    elif result_count < 20:
        return "MEDIUM"
    else:
        return "HIGH"


def check_competitor_eligibility(results_df: pd.DataFrame, competitor_name: str, event: str) -> Tuple[bool, str, int]:
    """
    Check if a competitor meets minimum data requirements.

    Args:
        results_df: Historical results DataFrame
        competitor_name: Competitor name to check
        event: Event code ('UH' or 'SB')

    Returns:
        Tuple of (is_eligible: bool, message: str, result_count: int)
    """
    result_count = get_competitor_result_count(results_df, competitor_name, event)
    confidence = get_data_confidence_level(result_count)

    if confidence == "BLOCKED":
        message = (
            f"BLOCKED: {competitor_name} has only {result_count} historical {event} results\n"
            f"  Absolute minimum: {ABSOLUTE_MINIMUM_RESULTS} results required\n"
            f"  Please add historical times before using this competitor"
        )
        return False, message, result_count
    elif confidence == "LOW":
        message = (
            f"WARNING: {competitor_name} has only {result_count} historical {event} results\n"
            f"  Recommended minimum: {RECOMMENDED_MINIMUM_RESULTS} results for high confidence\n"
            f"  Predictions will be less reliable (expect 5-10s error)"
        )
        return True, message, result_count
    else:
        return True, "", result_count


def validate_all_competitors_eligibility(
    results_df: pd.DataFrame, competitor_names: List[str], event: str
) -> Tuple[List[str], List[str], List[str]]:
    """
    Validate all competitors in a list for minimum data requirements.

    Args:
        results_df: Historical results DataFrame
        competitor_names: List of competitor names to check
        event: Event code ('UH' or 'SB')

    Returns:
        Tuple of (blocked_competitors, warned_competitors, messages)
    """
    blocked = []
    warned = []
    messages = []

    for name in competitor_names:
        is_eligible, message, count = check_competitor_eligibility(results_df, name, event)

        if not is_eligible:
            blocked.append(name)
            messages.append(message)
        elif message:  # Has warning but not blocked
            warned.append(name)
            messages.append(message)

    return blocked, warned, messages


# ===== HIGH-VARIANCE DIAMETER DETECTION =====
# Based on empirical analysis of 1003 historical results:
# - Diameters with CoV > 60% show unpredictable performance
# - These diameters produce wide prediction error spreads
# - High variance may indicate inconsistent wood quality or measurement errors

HIGH_VARIANCE_DIAMETERS = {
    279: 71,  # CoV = 71% (HIGHEST VARIANCE)
    254: 67,  # CoV = 67%
    270: 63,  # CoV = 63%
    275: 61,  # CoV = 61%
}

HIGH_VARIANCE_THRESHOLD_COV = 60  # Coefficient of Variation threshold (%)


def is_high_variance_diameter(diameter_mm: float) -> bool:
    """
    Check if diameter is known to have high performance variance.

    Args:
        diameter_mm: Block diameter in millimeters

    Returns:
        bool: True if diameter has high variance (CoV > 60%)
    """
    diameter_rounded = round(diameter_mm)
    return diameter_rounded in HIGH_VARIANCE_DIAMETERS


def get_diameter_variance_warning(diameter_mm: float) -> Optional[str]:
    """
    Get warning message for high-variance diameters.

    Args:
        diameter_mm: Block diameter in millimeters

    Returns:
        str: Warning message if high variance, None otherwise
    """
    diameter_rounded = round(diameter_mm)
    if diameter_rounded in HIGH_VARIANCE_DIAMETERS:
        cov = HIGH_VARIANCE_DIAMETERS[diameter_rounded]
        warning = (
            f"WARNING: {diameter_rounded}mm diameter has HIGH PERFORMANCE VARIANCE\n"
            f"  Historical coefficient of variation: {cov}%\n"
            f"  Predictions for this diameter may be less reliable\n"
            f"  Expect wider spread in finish times even with optimal handicaps\n"
            f"  Recommendation: Consider using standard diameters (300mm, 250mm, 225mm)"
        )
        return warning
    return None


def check_diameter_sample_size(results_df: pd.DataFrame, diameter_mm: float, event: str) -> Tuple[int, str]:
    """
    Check how many historical results exist for a given diameter.

    Args:
        results_df: Historical results DataFrame
        diameter_mm: Block diameter in millimeters
        event: Event code ('UH' or 'SB')

    Returns:
        Tuple of (sample_count: int, confidence_level: str)
    """
    if results_df is None or results_df.empty:
        return 0, "NO DATA"

    # Filter by event and diameter (within ±5mm tolerance)
    event = event.upper()
    diameter_data = results_df[
        (results_df["event"] == event)
        & (results_df["size_mm"] >= diameter_mm - 5)
        & (results_df["size_mm"] <= diameter_mm + 5)
    ]

    sample_count = len(diameter_data)

    # Determine confidence level
    if sample_count < 5:
        confidence = "VERY LOW"
    elif sample_count < 15:
        confidence = "LOW"
    elif sample_count < 30:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    return sample_count, confidence
