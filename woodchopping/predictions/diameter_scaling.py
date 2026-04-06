"""
Diameter-based time scaling for woodchopping predictions.

This module handles scaling chopping times when historical data is from different
wood diameters than the target prediction diameter. This is critical for accurate
predictions when competitors have limited data in the exact size being competed.

Key Concepts:
- Larger diameter = More wood to chop = Slower times
- Smaller diameter = Less wood to chop = Faster times
- Scaling relationship is approximately exponential (diameter^1.3 to diameter^1.5)

The scaling exponent is calibrated from empirical data where available.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from woodchopping.data import standardize_results_data

# Default scaling exponent (can be overridden with empirical calibration)
DEFAULT_SCALING_EXPONENT = 1.4

# Diameter tolerance for "close enough" matches (mm)
DIAMETER_TOLERANCE = 10

# Cache calibrated exponents per event
_event_exponent_cache: Dict[str, float] = {}


@dataclass
class ScalingMetadata:
    """Metadata about diameter scaling applied to a prediction."""

    was_scaled: bool
    original_diameter: Optional[float]
    target_diameter: Optional[float]
    scaling_factor: float
    confidence_adjustment: str  # "" (no change), "downgrade"
    warning_message: str


def calculate_scaling_factor(
    from_diameter: float, to_diameter: float, exponent: float = DEFAULT_SCALING_EXPONENT
) -> float:
    """
    Calculate time scaling factor based on diameter difference.

    Theory: Chopping time scales with wood volume/area to be cut.
    - Volume scales with diameter^2
    - But actual chopping efficiency doesn't scale linearly
    - Empirically, exponent between 1.3-1.5 works best

    Args:
        from_diameter: Diameter of historical data (mm)
        to_diameter: Target diameter for prediction (mm)
        exponent: Scaling exponent (default 1.4)

    Returns:
        Scaling factor to multiply time by

    Example:
        >>> # Moses: 29s in 325mm, predict for 275mm
        >>> factor = calculate_scaling_factor(325, 275)
        >>> scaled_time = 29 * factor
        >>> print(f"{scaled_time:.1f}s")  # ~24.5s
    """
    if abs(from_diameter - to_diameter) < DIAMETER_TOLERANCE:
        return 1.0

    # Ratio of diameters
    ratio = to_diameter / from_diameter

    # Time scales with diameter^exponent
    # If target is smaller (ratio < 1), scaling_factor < 1 (faster)
    # If target is larger (ratio > 1), scaling_factor > 1 (slower)
    scaling_factor = ratio**exponent

    return scaling_factor


def scale_time(
    time_seconds: float,
    from_diameter: float,
    to_diameter: float,
    exponent: float = DEFAULT_SCALING_EXPONENT,
) -> Tuple[float, ScalingMetadata]:
    """
    Scale a single time value for diameter difference.

    Args:
        time_seconds: Original time
        from_diameter: Original diameter (mm)
        to_diameter: Target diameter (mm)
        exponent: Scaling exponent

    Returns:
        Tuple of (scaled_time, metadata)
    """
    factor = calculate_scaling_factor(from_diameter, to_diameter, exponent)
    scaled_time = time_seconds * factor

    # Determine if scaling was significant
    was_scaled = abs(factor - 1.0) > 0.05  # More than 5% adjustment

    # Generate warning message
    if was_scaled:
        diameter_diff = abs(to_diameter - from_diameter)
        direction = "smaller" if to_diameter < from_diameter else "larger"
        warning = (
            f"Scaled from {from_diameter:.0f}mm to {to_diameter:.0f}mm ({direction}, {diameter_diff:.0f}mm difference)"
        )
    else:
        warning = ""

    # Confidence adjustment
    diameter_diff = abs(to_diameter - from_diameter)
    if diameter_diff > 50:
        confidence_adj = "downgrade"  # e.g., 275mm vs 350mm
    elif diameter_diff > 25:
        confidence_adj = "downgrade"  # e.g., 275mm vs 325mm
    else:
        confidence_adj = ""

    metadata = ScalingMetadata(
        was_scaled=was_scaled,
        original_diameter=from_diameter if was_scaled else None,
        target_diameter=to_diameter if was_scaled else None,
        scaling_factor=factor,
        confidence_adjustment=confidence_adj,
        warning_message=warning,
    )

    return scaled_time, metadata


def scale_time_list(
    times: List[float],
    from_diameter: float,
    to_diameter: float,
    exponent: float = DEFAULT_SCALING_EXPONENT,
) -> Tuple[List[float], ScalingMetadata]:
    """
    Scale a list of times for diameter difference.

    Args:
        times: List of time values
        from_diameter: Original diameter (mm)
        to_diameter: Target diameter (mm)
        exponent: Scaling exponent

    Returns:
        Tuple of (scaled_times, metadata)
    """
    factor = calculate_scaling_factor(from_diameter, to_diameter, exponent)
    scaled_times = [t * factor for t in times]

    # Use scale_time to generate consistent metadata
    _, metadata = scale_time(times[0] if times else 0, from_diameter, to_diameter, exponent)

    return scaled_times, metadata


def adjust_confidence_for_scaling(original_confidence: str, metadata: ScalingMetadata) -> str:
    """
    Adjust confidence level when diameter scaling is applied.

    Cross-diameter predictions are less reliable than exact-match predictions.

    Args:
        original_confidence: "HIGH", "MEDIUM", or "LOW"
        metadata: Scaling metadata from scale_time()

    Returns:
        Adjusted confidence level
    """
    if metadata.confidence_adjustment != "downgrade":
        return original_confidence

    confidence_map = {"HIGH": "MEDIUM", "MEDIUM": "LOW", "LOW": "LOW"}

    return confidence_map.get(original_confidence, original_confidence)


def calibrate_scaling_exponent(results_df: pd.DataFrame, event_code: str, min_samples: int = 5) -> Optional[float]:
    """
    Calibrate scaling exponent from competitors with results in multiple diameters.

    This function finds competitors who have times in multiple wood sizes and
    calculates the best-fit exponent for the scaling relationship.

    Args:
        results_df: Historical results DataFrame
        event_code: Event type (SB or UH)
        min_samples: Minimum number of cross-diameter pairs needed

    Returns:
        Calibrated exponent, or None if insufficient data

    Algorithm:
        1. Find competitors with results in 2+ different diameters
        2. For each pair of diameters, calculate actual time ratio
        3. Fit diameter_ratio^exponent to match time_ratio
        4. Return median exponent across all pairs
    """
    if results_df is None or results_df.empty:
        return None

    # Filter to this event
    event_data = results_df[results_df["event"] == event_code].copy()

    if len(event_data) < min_samples:
        return None

    # Find competitors with multiple diameter sizes
    competitor_diameters = event_data.groupby("competitor_name")["size_mm"].nunique()
    multi_diameter_competitors = competitor_diameters[competitor_diameters >= 2].index

    if len(multi_diameter_competitors) == 0:
        return None

    exponents = []

    for comp in multi_diameter_competitors:
        comp_data = event_data[event_data["competitor_name"] == comp]

        # Get average time for each diameter
        diameter_times = comp_data.groupby("size_mm")["raw_time"].mean()

        if len(diameter_times) < 2:
            continue

        # Compare all pairs of diameters
        diameters = sorted(diameter_times.index)
        for i in range(len(diameters)):
            for j in range(i + 1, len(diameters)):
                d1, d2 = diameters[i], diameters[j]
                t1, t2 = diameter_times[d1], diameter_times[d2]

                if t1 <= 0 or t2 <= 0:
                    continue

                # Calculate what exponent gives us the observed time ratio
                # t2/t1 = (d2/d1)^exp
                # exp = log(t2/t1) / log(d2/d1)
                time_ratio = t2 / t1
                diameter_ratio = d2 / d1

                if diameter_ratio <= 1.0:
                    continue

                exponent = np.log(time_ratio) / np.log(diameter_ratio)

                # Sanity check: exponent should be between 0.5 and 3.0
                if 0.5 <= exponent <= 3.0:
                    exponents.append(exponent)

    if len(exponents) < 3:  # Need at least a few samples
        return None

    # Return median exponent (robust to outliers)
    return float(np.median(exponents))


def get_event_scaling_exponent(results_df: Optional[pd.DataFrame], event_code: str) -> float:
    """
    Return a calibrated diameter scaling exponent for an event.

    Falls back to the default exponent when calibration is not possible.
    """
    event_key = str(event_code).strip().upper()
    if event_key in _event_exponent_cache:
        return _event_exponent_cache[event_key]

    if results_df is None or results_df.empty:
        _event_exponent_cache[event_key] = DEFAULT_SCALING_EXPONENT
        return DEFAULT_SCALING_EXPONENT

    results_df, _ = standardize_results_data(results_df)

    exponent = calibrate_scaling_exponent(results_df, event_key)
    if exponent is None:
        exponent = DEFAULT_SCALING_EXPONENT

    _event_exponent_cache[event_key] = float(exponent)
    return float(exponent)


def get_diameter_info_from_historical_data(
    results_df: pd.DataFrame, competitor_name: str, event_code: str
) -> Optional[float]:
    """
    Get the predominant diameter from a competitor's historical data.

    Args:
        results_df: Historical results
        competitor_name: Competitor name
        event_code: Event type

    Returns:
        Most common diameter in competitor's history, or None
    """
    if results_df is None or results_df.empty:
        return None
    required_cols = {"competitor_name", "event", "size_mm"}
    if not required_cols.issubset(results_df.columns):
        return None

    comp_data = results_df[(results_df["competitor_name"] == competitor_name) & (results_df["event"] == event_code)]

    if len(comp_data) == 0:
        return None

    # Return most common diameter
    diameter_counts = comp_data["size_mm"].value_counts()
    if len(diameter_counts) == 0:
        return None

    return float(diameter_counts.index[0])
