"""
Baseline Prediction Functions for Woodchopping Handicap System

This module provides statistical baseline calculations using historical performance data.
It implements cascading fallback logic to handle sparse data scenarios.

Functions:
    calculate_performance_weight() - Calculate exponential time-decay weight for historical results
    get_competitor_historical_times_flexible() - Get competitor's historical times with fallback
    get_event_baseline_flexible() - Calculate event baseline with cascading fallback
"""

import statistics
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from config import data_req, baseline_v2_config, rules
from woodchopping.data import standardize_results_data, load_wood_data
from woodchopping.predictions.diameter_scaling import scale_time, get_event_scaling_exponent

def calculate_performance_weight(
    result_date: Optional[datetime],
    reference_date: Optional[datetime] = None,
    half_life_days: int = 730
) -> float:
    """
    Calculate exponential time-decay weight for a historical performance result.

    Uses exponential decay formula: weight = 0.5^(days_old / half_life_days)

    This ensures recent performances have much greater influence than old performances,
    which is critical for aging competitors whose recent ability differs from their peak.

    Args:
        result_date: Date when the performance occurred (datetime or None)
        reference_date: Date to calculate age from (defaults to today)
        half_life_days: Number of days for weight to decay to 0.5 (default: 730 = 2 years)

    Returns:
        float: Weight between 0.0 and 1.0
            - Returns 1.0 if result_date is None (missing date = no decay)
            - Returns 1.0 if result is from today
            - Returns 0.5 if result is exactly half_life_days old
            - Returns ~0.0 for very old results (15+ years)

    Weight Examples (730-day / 2-year half-life):
        Current season (0-180 days): weight 0.87-1.00
        Last season (365 days): weight 0.71
        2 years ago (730 days): weight 0.50
        3 years ago (1095 days): weight 0.35
        4 years ago (1460 days): weight 0.25
        6 years ago (2190 days): weight 0.125
        10 years ago (3650 days): weight 0.031 (~3% of current)
        15 years ago (5475 days): weight 0.006 (~0.6% of current, essentially zero)

    Example:
        >>> from datetime import datetime
        >>> result_from_2020 = datetime(2020, 7, 15)
        >>> today = datetime(2025, 7, 15)  # 5 years = 1825 days later
        >>> weight = calculate_performance_weight(result_from_2020, today, 730)
        >>> print(f"{weight:.3f}")  # Should be ~0.177 (2^(-1825/730) = 2^(-2.5))
        0.177

    Note:
        - Designed for seasonal sport (American woodchopping: April-September)
        - 730-day (2-year) half-life balances recent trajectory vs career history
        - Performances from 10+ years ago have weight < 0.05
        - Missing dates return weight 1.0 to maintain backward compatibility
    """
    # If no date provided, return full weight (backward compatibility)
    if result_date is None or pd.isna(result_date):
        return 1.0

    # Default to current date if not specified
    if reference_date is None:
        reference_date = datetime.now()

    # Calculate days between dates
    try:
        # Handle both datetime and pandas Timestamp objects
        if isinstance(result_date, str):
            result_date = pd.to_datetime(result_date)
        if isinstance(reference_date, str):
            reference_date = pd.to_datetime(reference_date)

        days_old = (reference_date - result_date).days

        # Can't have negative age (future dates get full weight)
        if days_old < 0:
            return 1.0

        # Exponential decay: weight = 0.5^(days_old / half_life)
        # This is equivalent to: weight = 2^(-days_old / half_life)
        weight = 0.5 ** (days_old / half_life_days)

        return weight

    except Exception as e:
        # If date parsing fails, return full weight
        print(f"Warning: Failed to calculate weight for date {result_date}: {e}")
        return 1.0


def compute_robust_weighted_mean(
    historical_data: List[Tuple[float, Optional[datetime], float]]
) -> Tuple[Optional[float], float, float]:
    """
    Compute a robust weighted mean from (time, date, weight) tuples.

    Returns:
        Tuple of (mean_or_none, avg_weight, effective_n)
    """
    if not historical_data:
        return None, 0.0, 0.0

    times = np.array([t for t, _, _ in historical_data], dtype=float)
    weights = np.array([w for _, _, w in historical_data], dtype=float)

    weight_sum = weights.sum()
    if weight_sum <= 0:
        return float(np.mean(times)), 0.0, 0.0

    # Use median/MAD clipping to reduce influence of extreme values
    median = float(np.median(times))
    if len(times) < 5:
        return median, float(weight_sum / len(times)), float(weight_sum)

    mad = float(np.median(np.abs(times - median)))
    if mad > 0:
        clip_low = median - 2.5 * mad
        clip_high = median + 2.5 * mad
        clipped = np.clip(times, clip_low, clip_high)
    else:
        clipped = times

    mean = float(np.average(clipped, weights=weights))
    avg_weight = float(weight_sum / len(times))
    effective_n = float(weight_sum)
    return mean, avg_weight, effective_n


def compute_robust_mean(times: List[float]) -> Optional[float]:
    """Compute a robust mean using the weighted helper with unit weights."""
    if not times:
        return None
    data = [(t, None, 1.0) for t in times]
    mean, _, _ = compute_robust_weighted_mean(data)
    return mean


def apply_shrinkage(
    competitor_baseline: float,
    effective_n: float,
    event_baseline: Optional[float],
    shrinkage_k: float = 5.0
) -> float:
    """
    Apply simple empirical-Bayes shrinkage toward event baseline.
    """
    if event_baseline is None or effective_n <= 0:
        return competitor_baseline

    weight = effective_n / (effective_n + shrinkage_k)
    return (weight * competitor_baseline) + ((1.0 - weight) * event_baseline)


_wood_hardness_cache: Optional[Dict[str, float]] = None
_species_exponent_cache: Dict[str, float] = {}


def _build_wood_hardness_index(wood_df: pd.DataFrame) -> Dict[str, float]:
    """
    Build a composite hardness index using all available wood properties.

    Returns a mapping of speciesID -> hardness_factor (around 1.0).
    """
    if wood_df is None or wood_df.empty:
        return {}

    numeric_cols = ['janka_hard', 'spec_gravity', 'crush_strength', 'shear', 'MOR', 'MOE']
    available = [c for c in numeric_cols if c in wood_df.columns]
    if not available:
        return {}

    df = wood_df.copy()
    for col in available:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Z-score normalize each column to combine scales
    zcols = []
    for col in available:
        mean = df[col].mean()
        std = df[col].std()
        if std and std > 0:
            z = (df[col] - mean) / std
        else:
            z = pd.Series(0.0, index=df.index)
        zcols.append(z)

    if not zcols:
        return {}

    composite = sum(zcols) / len(zcols)

    # Map composite z-score to a bounded factor
    factor = (1.0 + (composite * 0.05)).clip(lower=0.85, upper=1.15)

    hardness_map: Dict[str, float] = {}
    if 'speciesID' in df.columns:
        for idx, row in df.iterrows():
            code = str(row['speciesID']).strip()
            if code:
                hardness_map[code] = float(factor.loc[idx])

    return hardness_map


def get_species_hardness_factor(species_code: str, wood_df: Optional[pd.DataFrame] = None) -> float:
    """Return composite hardness factor for a species (defaults to 1.0)."""
    global _wood_hardness_cache
    if wood_df is None:
        wood_df = load_wood_data()

    if _wood_hardness_cache is None:
        _wood_hardness_cache = _build_wood_hardness_index(wood_df)

    return _wood_hardness_cache.get(str(species_code).strip(), 1.0)


def calibrate_species_exponent(
    results_df: pd.DataFrame,
    wood_df: Optional[pd.DataFrame],
    event_code: str,
    min_species_samples: int = 5
) -> float:
    """
    Calibrate exponent for species hardness normalization from historical data.
    """
    cache_key = str(event_code).upper()
    if cache_key in _species_exponent_cache:
        return _species_exponent_cache[cache_key]

    if results_df is None or results_df.empty:
        _species_exponent_cache[cache_key] = 0.4
        return 0.4

    df = results_df[results_df['event'] == event_code].copy()
    if df.empty or 'species' not in df.columns or 'size_mm' not in df.columns:
        _species_exponent_cache[cache_key] = 0.4
        return 0.4

    wood_df = wood_df if wood_df is not None else load_wood_data()

    # Normalize all times to 300mm to isolate species effect
    def _scale_to_standard(row):
        time_val = row.get('raw_time')
        size_val = row.get('size_mm')
        species_val = row.get('species')
        if pd.isna(time_val) or pd.isna(size_val):
            return np.nan
        exponent = get_event_scaling_exponent(results_df, event_code)
        scaled, _ = scale_time(
            float(time_val),
            float(size_val),
            300.0,
            exponent=exponent
        )
        return scaled

    df['scaled_time'] = df.apply(_scale_to_standard, axis=1)

    # Aggregate by species
    grouped = df.groupby('species')['scaled_time'].agg(['median', 'count']).reset_index()
    grouped = grouped[grouped['count'] >= min_species_samples].copy()
    if grouped.empty:
        _species_exponent_cache[cache_key] = 0.4
        return 0.4

    grouped['hardness_factor'] = grouped['species'].apply(
        lambda s: get_species_hardness_factor(s, wood_df)
    )

    # Fit exponent by minimizing MAE in log space
    hardness = grouped['hardness_factor'].values.astype(float)
    times = grouped['median'].values.astype(float)
    counts = grouped['count'].values.astype(float)

    if np.any(hardness <= 0) or np.any(times <= 0):
        _species_exponent_cache[cache_key] = 0.4
        return 0.4

    log_h = np.log(hardness)
    log_t = np.log(times)

    if np.allclose(log_h, 0):
        _species_exponent_cache[cache_key] = 0.4
        return 0.4

    weights = counts / counts.sum() if counts.sum() > 0 else None

    best_exp = 0.4
    best_err = float('inf')
    candidates = np.arange(0.1, 2.51, 0.05)

    for exp in candidates:
        residuals = log_t - (exp * log_h)
        if weights is not None:
            log_k = float(np.average(residuals, weights=weights))
            pred = log_k + (exp * log_h)
            err = float(np.average(np.abs(log_t - pred), weights=weights))
        else:
            log_k = float(np.mean(residuals))
            pred = log_k + (exp * log_h)
            err = float(np.mean(np.abs(log_t - pred)))

        if err < best_err:
            best_err = err
            best_exp = exp

    exponent = float(np.clip(best_exp, 0.1, 2.5))
    _species_exponent_cache[cache_key] = exponent
    return exponent


def normalize_time_to_target(
    time_val: float,
    hist_species: str,
    hist_diameter: float,
    target_species: str,
    target_diameter: float,
    event_code: str,
    wood_df: Optional[pd.DataFrame],
    results_df: Optional[pd.DataFrame] = None,
    quality: Optional[float] = None
) -> Tuple[float, str]:
    """
    Normalize a historical time to target species and diameter.
    """
    if time_val is None:
        return time_val, "no time"

    quality_val = int(quality) if quality is not None and not pd.isna(quality) else 5
    quality_val = max(1, min(10, quality_val))

    normalized = float(time_val)
    notes = []

    # Normalize historical time to quality 5 reference
    if quality_val != 5:
        quality_offset = quality_val - 5
        quality_factor = 1.0 + (quality_offset * 0.02)
        if quality_factor > 0:
            normalized = normalized / quality_factor
            notes.append(f"Quality normalized: {quality_val} -> 5")

    if hist_diameter and target_diameter and hist_diameter != target_diameter:
        exponent = get_event_scaling_exponent(results_df, event_code)
        scaled_time, metadata = scale_time(
            float(time_val),
            float(hist_diameter),
            float(target_diameter),
            exponent=exponent
        )
        normalized = scaled_time
        if metadata.warning_message:
            notes.append(f"{metadata.warning_message} (exp {exponent:.2f})")

    hist_species_clean = str(hist_species).strip() if hist_species is not None and not pd.isna(hist_species) else ""
    target_species_clean = str(target_species).strip() if target_species is not None else ""

    if hist_species_clean and target_species_clean:
        hist_factor = get_species_hardness_factor(hist_species_clean, wood_df)
        target_factor = get_species_hardness_factor(target_species_clean, wood_df)

        if hist_factor > 0 and target_factor > 0 and hist_factor != target_factor:
            exponent = calibrate_species_exponent(
                results_df=results_df,
                wood_df=wood_df,
                event_code=event_code
            )
            normalized = normalized * ((target_factor / hist_factor) ** exponent)
            notes.append(f"Species normalization: {hist_factor:.3f} -> {target_factor:.3f} (exp {exponent:.2f})")

    return normalized, "; ".join(notes)


def get_competitor_historical_times_normalized(
    competitor_name: str,
    species: str,
    diameter: float,
    event_code: str,
    results_df: pd.DataFrame,
    return_weights: bool = False,
    reference_date: Optional[datetime] = None,
    wood_df: Optional[pd.DataFrame] = None
) -> Tuple[List, str, Dict[str, float]]:
    """
    Get competitor historical times normalized to target species/diameter.
    """
    if results_df is None or results_df.empty:
        return [], "no data available", {'scaled': False, 'max_diameter_diff': 0.0, 'species_normalized': False}

    results_df, _ = standardize_results_data(results_df)
    wood_df = wood_df if wood_df is not None else load_wood_data()

    name_match = results_df["competitor_name"].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    event_match = results_df["event"].astype(str).str.strip().str.upper() == event_code

    # Try exact species match first
    if species and "species" in results_df.columns:
        species_match = results_df["species"].astype(str).str.strip().str.lower() == str(species).strip().lower()
        matches = results_df[name_match & event_match & species_match]
        data_source = f"on {species} (exact match)"
    else:
        matches = results_df[name_match & event_match]
        data_source = "on various wood types"

    if matches.empty or len(matches) < data_req.MIN_HISTORICAL_TIMES:
        # Fallback: include any species for competitor+event if exact data is sparse
        any_species = results_df[name_match & event_match]
        if not any_species.empty:
            matches = pd.concat([matches, any_species]).drop_duplicates()
            data_source = "mixed species (normalized)"

    data = []
    meta = {'scaled': False, 'max_diameter_diff': 0.0, 'species_normalized': False}

    for _, row in matches.iterrows():
        time_val = row.get('raw_time')
        if time_val is None or time_val <= 0:
            continue

        hist_species = row.get('species')
        hist_diameter = row.get('size_mm')
        hist_quality = row.get('quality', 5)

        normalized, _ = normalize_time_to_target(
            float(time_val),
            str(hist_species).strip(),
            float(hist_diameter) if hist_diameter is not None else None,
            str(species).strip(),
            float(diameter) if diameter is not None else None,
            event_code,
            wood_df,
            results_df=results_df,
            quality=hist_quality
        )

        if hist_diameter is not None and diameter is not None:
            diff = abs(float(hist_diameter) - float(diameter))
            if diff > 0:
                meta['scaled'] = True
                meta['max_diameter_diff'] = max(meta['max_diameter_diff'], diff)

        if (
            hist_species is not None and not pd.isna(hist_species)
            and species and str(hist_species).strip().lower() != str(species).strip().lower()
        ):
            meta['species_normalized'] = True

        if return_weights:
            date = row.get('date')
            weight = calculate_performance_weight(date, reference_date)
            data.append((normalized, date, weight))
        else:
            data.append(normalized)

    if data:
        return data, data_source, meta

    return [], "no competitor history found", meta


def predict_baseline_time(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: Optional[float],
    event_code: str,
    results_df: pd.DataFrame,
    wood_df: Optional[pd.DataFrame] = None
) -> Tuple[Optional[float], str, str]:
    """
    Predict time using baseline-only logic with normalization.

    Returns:
        Tuple of (predicted_time, confidence, explanation)
    """
    if results_df is None or results_df.empty:
        return None, "LOW", "no data available"

    results_df, _ = standardize_results_data(results_df)
    wood_df = wood_df if wood_df is not None else load_wood_data()

    historical_data, data_source, normalization_meta = get_competitor_historical_times_normalized(
        competitor_name,
        species,
        diameter,
        event_code,
        results_df,
        return_weights=True,
        wood_df=wood_df
    )

    if len(historical_data) >= 3:
        baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
        event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df, wood_df=wood_df)
        if event_baseline is not None and baseline is not None:
            baseline = apply_shrinkage(baseline, effective_n, event_baseline)
            explanation = f"Robust history ({data_source}, {len(historical_data)} results) + shrinkage to {event_source}"
        else:
            explanation = f"Robust history ({data_source}, {len(historical_data)} results)"
        confidence = "HIGH"
    elif len(historical_data) > 0:
        baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
        event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df, wood_df=wood_df)
        if event_baseline is not None and baseline is not None:
            baseline = apply_shrinkage(baseline, effective_n, event_baseline)
            explanation = f"Limited history ({data_source}, {len(historical_data)} results) + shrinkage to {event_source}"
        else:
            explanation = f"Limited history ({data_source}, {len(historical_data)} results)"
        confidence = "MEDIUM"
    else:
        baseline, baseline_source = get_event_baseline_flexible(species, diameter, event_code, results_df, wood_df=wood_df)
        if baseline is not None:
            explanation = f"Event baseline ({baseline_source})"
            confidence = "LOW"
        else:
            baseline = None
            explanation = "No baseline available"
            confidence = "LOW"

    if baseline is None:
        return None, confidence, explanation

    quality_val = int(quality) if quality is not None and not pd.isna(quality) else 5
    quality_val = max(1, min(10, quality_val))
    if quality_val != 5:
        quality_offset = quality_val - 5
        quality_factor = 1.0 + (quality_offset * 0.02)
        baseline = baseline * quality_factor
        adjustment_pct = (quality_factor - 1.0) * 100
        if quality_val < 5:
            explanation += f" [Quality {quality_val}/10: softer, {adjustment_pct:+.0f}%]"
        else:
            explanation += f" [Quality {quality_val}/10: harder, {adjustment_pct:+.0f}%]"

    if normalization_meta.get('max_diameter_diff', 0.0) > 25 or normalization_meta.get('species_normalized', False):
        if confidence == "HIGH":
            confidence = "MEDIUM"
        elif confidence == "MEDIUM":
            confidence = "LOW"
        explanation += " [Normalized sizes/species]"

    return baseline, confidence, explanation


def backtest_baseline_predictions(
    results_df: pd.DataFrame,
    wood_df: Optional[pd.DataFrame] = None,
    event_code: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, float]:
    """
    Backtest baseline predictions using leave-one-out evaluation.
    """
    if results_df is None or results_df.empty:
        return {'count': 0}

    results_df, _ = standardize_results_data(results_df)
    wood_df = wood_df if wood_df is not None else load_wood_data()
    if event_code:
        results_df = results_df[results_df['event'] == event_code].copy()

    if results_df.empty:
        return {'count': 0}

    if limit and limit < len(results_df):
        results_df = results_df.sample(n=limit, random_state=42)

    errors = []
    abs_errors = []
    sq_errors = []
    pct_errors = []

    for idx, row in results_df.iterrows():
        train_df = results_df.drop(index=idx)
        pred, _, _ = predict_baseline_time(
            row.get('competitor_name'),
            row.get('species'),
            row.get('size_mm'),
            row.get('quality'),
            row.get('event'),
            train_df,
            wood_df=wood_df
        )

        actual = row.get('raw_time')
        if pred is None or actual is None or actual <= 0:
            continue

        err = pred - actual
        errors.append(err)
        abs_errors.append(abs(err))
        sq_errors.append(err ** 2)
        if actual > 0:
            pct_errors.append(abs(err) / actual)

    count = len(errors)
    if count == 0:
        return {'count': 0}

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(sq_errors)))
    mape = float(np.mean(pct_errors)) * 100 if pct_errors else 0.0
    bias = float(np.mean(errors))

    return {
        'count': count,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'bias': bias
    }


def get_competitor_historical_times_flexible(
    competitor_name: str,
    species: str,
    event_code: str,
    results_df: pd.DataFrame,
    return_weights: bool = False,
    reference_date: Optional[datetime] = None
) -> Tuple[List, str]:
    """
    Get competitor's historical times with flexible fallback logic.

    Tries in order:
    1. Exact match: competitor + event + species
    2. Fallback: competitor + event (any species)

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame
        return_weights: If True, returns tuples of (time, date, weight) instead of just times
        reference_date: Date to calculate weights from (defaults to today)

    Returns:
        Tuple of (list of data, data source description)

        If return_weights=False (default):
            Returns (List[float], str) - list of times and source description

        If return_weights=True:
            Returns (List[Tuple[float, datetime, float]], str)
            Each tuple is (time, date, weight) where weight is calculated via time-decay

        Returns ([], error_message) if no data found

    Example (backward compatible):
        >>> times, source = get_competitor_historical_times_flexible(
        ...     "John Smith", "White Pine", "SB", results_df
        ... )
        >>> if times:
        ...     avg = statistics.mean(times)

    Example (with weights):
        >>> data, source = get_competitor_historical_times_flexible(
        ...     "John Smith", "White Pine", "SB", results_df, return_weights=True
        ... )
        >>> if data:
        ...     weighted_avg = sum(t*w for t,d,w in data) / sum(w for t,d,w in data)
    """
    if results_df is None or results_df.empty:
        return [], "no data available"

    results_df, _ = standardize_results_data(results_df)

    # Match competitor and event (required)
    name_match = results_df["competitor_name"].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    event_match = results_df["event"].astype(str).str.strip().str.upper() == event_code

    # Try exact species match first
    if species and "species" in results_df.columns:
        species_match = results_df["species"].astype(str).str.strip().str.lower() == str(species).strip().lower()
        exact_matches = results_df[name_match & event_match & species_match]

        data = []
        for _, row in exact_matches.iterrows():
            time = row.get('raw_time')
            if time is not None and time > 0:
                if return_weights:
                    date = row.get('date')
                    weight = calculate_performance_weight(date, reference_date)
                    data.append((time, date, weight))
                else:
                    data.append(time)

        if data:
            return data, f"on {species} (exact match)"

    # Fallback: any species for this competitor and event
    any_species_matches = results_df[name_match & event_match]
    data = []
    for _, row in any_species_matches.iterrows():
        time = row.get('raw_time')
        if time is not None and time > 0:
            if return_weights:
                date = row.get('date')
                weight = calculate_performance_weight(date, reference_date)
                data.append((time, date, weight))
            else:
                data.append(time)

    if data:
        return data, "on various wood types"

    return [], "no competitor history found"


def get_event_baseline_flexible(
    species: str,
    diameter: float,
    event_code: str,
    results_df: pd.DataFrame,
    wood_df: Optional[pd.DataFrame] = None
) -> Tuple[Optional[float], str]:
    """
    Calculate baseline with cascading fallback.

    Tries in order:
    1. Species + diameter range + event
    2. Diameter range + event (any species)
    3. Event only (any species, any diameter)

    Args:
        species: Wood species code
        diameter: Diameter in mm
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame

    Returns:
        Tuple of (baseline_time, data source description)
        Returns (None, error_message) if insufficient data

    Example:
        >>> baseline, source = get_event_baseline_flexible(
        ...     "White Pine", 300, "SB", results_df
        ... )
        >>> if baseline:
        ...     print(f"Event baseline: {baseline:.1f}s from {source}")
    """
    if results_df is None or results_df.empty:
        return None, "no data available"

    results_df, _ = standardize_results_data(results_df)
    wood_df = wood_df if wood_df is not None else load_wood_data()

    event_match = results_df["event"].astype(str).str.strip().str.upper() == event_code

    # Try species + diameter range + event
    if species and "species" in results_df.columns and "size_mm" in results_df.columns:
        species_match = results_df["species"].astype(str).str.strip().str.lower() == str(species).strip().lower()
        diameter_match = (results_df["size_mm"] >= diameter - 25) & (results_df["size_mm"] <= diameter + 25)

        exact_matches = results_df[species_match & diameter_match & event_match]
        times = []
        for _, row in exact_matches.iterrows():
            time_val = row.get('raw_time')
            if time_val is not None and time_val > 0:
                normalized, _ = normalize_time_to_target(
                    float(time_val),
                    str(row.get('species')).strip(),
                    float(row.get('size_mm')) if row.get('size_mm') is not None else None,
                    str(species).strip(),
                    float(diameter),
                    event_code,
                    wood_df,
                    results_df=results_df,
                    quality=row.get('quality', 5)
                )
                times.append(normalized)

        if len(times) >= 3:
            mean_val = compute_robust_mean(times)
            return mean_val, f"species/size normalized average ({len(times)} performances)"

    # Fallback: diameter range + event (any species)
    if "size_mm" in results_df.columns:
        diameter_match = (results_df["size_mm"] >= diameter - 25) & (results_df["size_mm"] <= diameter + 25)
        size_matches = results_df[diameter_match & event_match]

        times = []
        for _, row in size_matches.iterrows():
            time_val = row.get('raw_time')
            if time_val is not None and time_val > 0:
                normalized, _ = normalize_time_to_target(
                    float(time_val),
                    str(row.get('species')).strip(),
                    float(row.get('size_mm')) if row.get('size_mm') is not None else None,
                    str(species).strip(),
                    float(diameter),
                    event_code,
                    wood_df,
                    results_df=results_df,
                    quality=row.get('quality', 5)
                )
                times.append(normalized)

        if len(times) >= 3:
            mean_val = compute_robust_mean(times)
            return mean_val, f"size normalized average ({len(times)} performances)"

    # Final fallback: event only (all data for this event type)
    event_only = results_df[event_match]
    times = []
    for _, row in event_only.iterrows():
        time_val = row.get('raw_time')
        if time_val is not None and time_val > 0:
            normalized, _ = normalize_time_to_target(
                float(time_val),
                str(row.get('species')).strip(),
                float(row.get('size_mm')) if row.get('size_mm') is not None else None,
                str(species).strip(),
                float(diameter),
                event_code,
                wood_df,
                results_df=results_df,
                quality=row.get('quality', 5)
            )
            times.append(normalized)

    if len(times) >= 3:
        mean_val = compute_robust_mean(times)
        return mean_val, f"event normalized average ({len(times)} performances)"

    return None, "insufficient data"


# ============================================================================
# PHASE 2: HYBRID BASELINE V2 - HIERARCHICAL MODEL FITTING
# ============================================================================

def get_competitor_median_diameter(
    competitor_name: str,
    event_code: str,
    results_df: pd.DataFrame
) -> float:
    """
    Calculate competitor's median diameter choice as skill proxy (selection bias feature).

    Key insight from data analysis: Diameter correlates NEGATIVELY with time (-0.36 to -0.38).
    This reveals selection bias:
    - Elite competitors choose larger diameters (300mm): mean 24-27s
    - Novices choose smaller diameters (250mm): mean 63-66s

    Median diameter choice is a strong indicator of skill level.

    Args:
        competitor_name: Competitor's name
        event_code: Event type (SB/UH)
        results_df: Historical results (cleaned via load_and_clean_results)

    Returns:
        Median diameter in mm (float). Returns 300.0 if no history.
    """
    if results_df is None or results_df.empty:
        return 300.0  # Default to standard competition diameter

    # Standardize if needed
    if 'size_mm' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    # Filter to competitor + event
    comp_match = results_df['competitor_name'].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    event_match = results_df['event'].astype(str).str.strip().str.upper() == event_code.upper()

    competitor_data = results_df[comp_match & event_match]

    if competitor_data.empty or 'size_mm' not in competitor_data.columns:
        return 300.0  # Default

    diameters = competitor_data['size_mm'].dropna()

    if len(diameters) == 0:
        return 300.0

    return float(diameters.median())


def estimate_diameter_curve(
    results_df: pd.DataFrame,
    event_code: str,
    wood_df: Optional[pd.DataFrame] = None,
    anchor_to_data: bool = True
) -> Dict[str, any]:
    """
    Estimate smooth diameter curve from historical data.

    Returns polynomial coefficients and statistics for diameter scaling effect.
    Uses data-driven approach anchored to actual competitor data.

    Args:
        results_df: Historical results (cleaned)
        event_code: Event type (SB/UH)
        wood_df: Wood properties DataFrame
        anchor_to_data: If True, blend data-driven curve with data anchors

    Returns:
        Dictionary with:
        - coefficients: [c0, c1, c2] for polynomial log(time) ~ c0 + c1*diameter + c2*diameter^2
        - r_squared: Model fit quality
        - sample_count: Number of observations used
        - diameter_range: (min, max) diameter observed
        - anchored: Whether data anchoring was applied
    """
    if results_df is None or results_df.empty:
        # Return default linear scaling if no data
        return {
            'coefficients': [3.0, 0.002, 0.0],  # Approximate log-linear
            'r_squared': 0.0,
            'sample_count': 0,
            'diameter_range': (225, 350),
            'anchored': False
        }

    # Standardize if needed
    if 'raw_time' not in results_df.columns or 'size_mm' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    # Filter to event
    event_data = results_df[results_df['event'].str.upper() == event_code.upper()].copy()

    if event_data.empty or len(event_data) < 10:
        return {
            'coefficients': [3.0, 0.002, 0.0],
            'r_squared': 0.0,
            'sample_count': 0,
            'diameter_range': (225, 350),
            'anchored': False
        }

    # Remove outliers (use configured thresholds)
    event_data = event_data[
        (event_data['raw_time'] >= data_req.MIN_VALID_TIME_SECONDS) &
        (event_data['raw_time'] <= data_req.MAX_VALID_TIME_SECONDS) &
        (event_data['size_mm'] >= data_req.MIN_DIAMETER_MM) &
        (event_data['size_mm'] <= data_req.MAX_DIAMETER_MM)
    ].copy()

    if len(event_data) < 10:
        return {
            'coefficients': [3.0, 0.002, 0.0],
            'r_squared': 0.0,
            'sample_count': 0,
            'diameter_range': (225, 350),
            'anchored': False
        }

    # Transform to log-space
    event_data['log_time'] = np.log(event_data['raw_time'])

    # Normalize diameter to [0, 1] for numerical stability
    diameter_min = event_data['size_mm'].min()
    diameter_max = event_data['size_mm'].max()
    diameter_range_val = diameter_max - diameter_min

    if diameter_range_val < 25:  # Too narrow, use defaults
        return {
            'coefficients': [3.0, 0.002, 0.0],
            'r_squared': 0.0,
            'sample_count': len(event_data),
            'diameter_range': (float(diameter_min), float(diameter_max)),
            'anchored': False
        }

    event_data['diameter_norm'] = (event_data['size_mm'] - diameter_min) / diameter_range_val

    # Fit quadratic polynomial in log-space: log(time) ~ c0 + c1*d + c2*d^2
    X = event_data[['diameter_norm']].values
    X_poly = np.column_stack([np.ones(len(X)), X, X**2])  # [1, d, d^2]
    y = event_data['log_time'].values

    try:
        # Weighted least squares (equal weights for now, can add time-decay later)
        coeffs_norm = np.linalg.lstsq(X_poly, y, rcond=None)[0]

        # Calculate R²
        y_pred = X_poly @ coeffs_norm
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Transform coefficients back to original diameter scale
        # log(time) = c0' + c1'*d_norm + c2'*d_norm^2
        # where d_norm = (d - d_min) / d_range
        # Expanding: log(time) = c0' + c1'*(d-d_min)/d_range + c2'*((d-d_min)/d_range)^2
        # Rearranging to log(time) = c0 + c1*d + c2*d^2:
        c0_orig = coeffs_norm[0] - (coeffs_norm[1] * diameter_min / diameter_range_val) + (coeffs_norm[2] * (diameter_min / diameter_range_val)**2)
        c1_orig = (coeffs_norm[1] / diameter_range_val) - (2 * coeffs_norm[2] * diameter_min / (diameter_range_val**2))
        c2_orig = coeffs_norm[2] / (diameter_range_val**2)

        return {
            'coefficients': [float(c0_orig), float(c1_orig), float(c2_orig)],
            'r_squared': float(r_squared),
            'sample_count': len(event_data),
            'diameter_range': (float(diameter_min), float(diameter_max)),
            'anchored': False
        }

    except np.linalg.LinAlgError:
        # Fallback to simple linear if polynomial fails
        return {
            'coefficients': [3.0, 0.002, 0.0],
            'r_squared': 0.0,
            'sample_count': len(event_data),
            'diameter_range': (float(diameter_min), float(diameter_max)),
            'anchored': False
        }


def _pooled_std_dev_by_event(
    competitor_data: pd.DataFrame,
    min_samples: int
) -> Optional[float]:
    if competitor_data.empty:
        return None

    times = competitor_data.get('raw_time')
    if times is None:
        return None

    total_samples = int(times.count())
    if total_samples < min_samples:
        return None

    if 'event' not in competitor_data.columns:
        std_dev = float(times.std(ddof=1)) if total_samples >= 2 else None
        return std_dev

    total_df = 0.0
    var_sum = 0.0
    for _, group in competitor_data.groupby('event'):
        group_times = group['raw_time'].dropna().astype(float)
        if len(group_times) < 2:
            continue
        var = float(group_times.var(ddof=1))
        df = float(len(group_times) - 1)
        var_sum += var * df
        total_df += df

    if total_df <= 0:
        return None

    return float(np.sqrt(var_sum / total_df))


def _global_fallback_std_dev(
    results_df: pd.DataFrame,
    min_samples: int
) -> Optional[float]:
    if results_df is None or results_df.empty:
        return None

    if 'raw_time' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    pooled_values = []
    for _, group in results_df.groupby('competitor_name'):
        pooled = _pooled_std_dev_by_event(group, min_samples)
        if pooled is not None:
            pooled_values.append(pooled)

    if not pooled_values:
        return None

    return float(np.median(pooled_values))


def estimate_competitor_std_dev(
    competitor_name: str,
    event_code: str,
    results_df: pd.DataFrame,
    min_std_dev: float = 1.5,
    max_std_dev: float = 6.0
) -> Tuple[float, str]:
    """
    Estimate competitor-specific standard deviation using all available history.

    Uses pooled variance across events for the competitor (data-driven and stable).
    Falls back to a dataset-level median std-dev when the competitor lacks samples.
    """
    if results_df is None or results_df.empty:
        return 3.0, "MODERATE"

    # Standardize if needed
    if 'raw_time' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    comp_match = results_df['competitor_name'].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    competitor_data = results_df[comp_match]

    pooled_std = _pooled_std_dev_by_event(competitor_data, baseline_v2_config.MIN_SAMPLES_FOR_STD_DEV)
    if pooled_std is None:
        pooled_std = _global_fallback_std_dev(results_df, baseline_v2_config.MIN_SAMPLES_FOR_STD_DEV)

    if pooled_std is None:
        pooled_std = rules.PERFORMANCE_VARIANCE_SECONDS

    std_dev = max(min_std_dev, min(float(pooled_std), max_std_dev))

    if std_dev <= baseline_v2_config.CONSISTENCY_VERY_HIGH_THRESHOLD:
        consistency_rating = "VERY HIGH"
    elif std_dev <= baseline_v2_config.CONSISTENCY_HIGH_THRESHOLD:
        consistency_rating = "HIGH"
    elif std_dev <= baseline_v2_config.CONSISTENCY_MODERATE_THRESHOLD:
        consistency_rating = "MODERATE"
    else:
        consistency_rating = "LOW"

    return std_dev, consistency_rating


def fit_hierarchical_regression(
    results_df: pd.DataFrame,
    wood_df: pd.DataFrame,
    hardness_index: Dict[str, float],
    adaptive_half_lives: Dict[str, int],
    event_code: Optional[str] = None
) -> Dict[str, any]:
    """
    Fit hierarchical regression model in log-space with time-decay weighting.

    Model structure:
    log(time_ij) = ?_event + f_diameter(diameter_i) + ?_hardness * hardness_index_i
                   + ?_selection * median_diam_j + u_competitor_j + ?_ij

    Where:
    - ?_event: Event intercept (SB/UH)
    - f_diameter: Smooth diameter curve (from estimate_diameter_curve)
    - ?_hardness: Wood hardness effect coefficient
    - ?_selection: Selection bias coefficient (median diameter as skill proxy)
    - u_competitor_j: Competitor random effect (with Empirical Bayes shrinkage)
    - ?_ij: Residual error

    Args:
        results_df: Historical results (cleaned via load_and_clean_results)
        wood_df: Wood properties
        hardness_index: Species -> hardness index mapping (from fit_wood_hardness_index)
        adaptive_half_lives: Competitor -> half-life mapping (from calculate_adaptive_half_lives)
        event_code: If specified, fit model for single event only

    Returns:
        Dictionary containing fitted model parameters:
        - event_intercepts: {event: intercept}
        - diameter_curves: {event: diameter_curve_dict}
        - hardness_coefficient: ?_hardness
        - selection_coefficient: ?_selection
        - competitor_effects: {competitor: effect}
        - competitor_std_devs: {competitor: std_dev}
        - global_std_dev: Overall residual std dev
        - sample_count: Number of observations
        - r_squared: Model fit quality
    """
    if results_df is None or results_df.empty:
        return _get_default_hierarchical_model()

    # Standardize if needed
    if 'raw_time' not in results_df.columns:
        from woodchopping.data import load_and_clean_results
        results_df = load_and_clean_results(results_df)

    # Filter to event if specified
    if event_code:
        results_df = results_df[results_df['event'].str.upper() == event_code.upper()].copy()

    if len(results_df) < baseline_v2_config.MIN_DATA_FOR_HIERARCHICAL_MODEL:
        return _get_default_hierarchical_model()

    # Remove outliers using configured thresholds
    results_df = results_df[
        (results_df['raw_time'] >= data_req.MIN_VALID_TIME_SECONDS) &
        (results_df['raw_time'] <= data_req.MAX_VALID_TIME_SECONDS) &
        (results_df['size_mm'] >= data_req.MIN_DIAMETER_MM) &
        (results_df['size_mm'] <= data_req.MAX_DIAMETER_MM)
    ].copy()

    if len(results_df) < baseline_v2_config.MIN_DATA_FOR_HIERARCHICAL_MODEL:
        return _get_default_hierarchical_model()

    # Transform to log-space
    results_df['log_time'] = np.log(results_df['raw_time'])

    # Calculate time-decay weights
    reference_date = results_df['date'].max() if 'date' in results_df.columns else datetime.now()

    def calc_weight(row):
        competitor = row.get('competitor_name', '')
        half_life = adaptive_half_lives.get(competitor, 730)
        return calculate_performance_weight(row.get('date'), reference_date, half_life)

    results_df['weight'] = results_df.apply(calc_weight, axis=1)

    # Add features
    results_df['hardness_idx'] = results_df['species'].map(hardness_index).fillna(1.0)
    results_df['median_diameter'] = results_df.apply(
        lambda row: get_competitor_median_diameter(row['competitor_name'], row['event'], results_df),
        axis=1
    )

    # Fit diameter curves per event (for diagnostics + metadata)
    events = results_df['event'].unique()
    diameter_curves = {}
    for event in events:
        diameter_curves[event] = estimate_diameter_curve(results_df, event, wood_df)

    # Build weighted least squares design matrix
    event_is_uh = (results_df['event'].str.upper() == 'UH').astype(float).values
    diameter = results_df['size_mm'].astype(float).values
    diameter_center = float(np.mean(diameter))
    diameter_centered = diameter - diameter_center
    diameter_centered_sq = diameter_centered ** 2

    hardness_vals = results_df['hardness_idx'].astype(float).values
    hardness_center = float(np.mean(hardness_vals)) if len(hardness_vals) else 1.0
    hardness_centered = hardness_vals - hardness_center

    selection_vals = results_df['median_diameter'].astype(float).values
    selection_center = float(baseline_v2_config.SELECTION_BIAS_DEFAULT_DIAMETER)
    selection_centered = selection_vals - selection_center

    # Columns: intercept, event_is_uh, d, d^2, event*d, event*d^2, hardness, selection
    X = np.column_stack([
        np.ones(len(results_df)),
        event_is_uh,
        diameter_centered,
        diameter_centered_sq,
        event_is_uh * diameter_centered,
        event_is_uh * diameter_centered_sq,
        hardness_centered,
        selection_centered
    ])

    y = results_df['log_time'].astype(float).values
    w = results_df['weight'].astype(float).values
    w = np.where(w > 0, w, 1.0)

    try:
        sqrt_w = np.sqrt(w)
        Xw = X * sqrt_w[:, None]
        yw = y * sqrt_w
        coeffs = np.linalg.lstsq(Xw, yw, rcond=None)[0]
    except np.linalg.LinAlgError:
        return _get_default_hierarchical_model()

    y_pred = X @ coeffs
    residuals = y - y_pred

    # Weighted R^2
    y_mean = np.average(y, weights=w)
    ss_res = np.sum(w * (residuals ** 2))
    ss_tot = np.sum(w * ((y - y_mean) ** 2))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Competitor random effects (shrink residual mean toward 0)
    competitor_effects = {}
    competitor_std_devs = {}
    shrinkage_k = 5.0
    for competitor, group in results_df.assign(residual=residuals).groupby('competitor_name'):
        weights = group['weight'].astype(float).values
        res = group['residual'].astype(float).values
        effective_n = float(weights.sum())
        if effective_n <= 0:
            continue
        mean_res = float(np.average(res, weights=weights))
        shrink = effective_n / (effective_n + shrinkage_k)
        competitor_effects[str(competitor).strip().lower()] = mean_res * shrink
        if len(res) >= baseline_v2_config.MIN_SAMPLES_FOR_STD_DEV:
            resid_mean = mean_res
            resid_var = float(np.average((res - resid_mean) ** 2, weights=weights))
            competitor_std_devs[str(competitor).strip().lower()] = float(np.sqrt(resid_var))

    global_std_dev = float(np.sqrt(np.average(residuals ** 2, weights=w)))

    # Derive event intercepts for reporting
    intercept = float(coeffs[0])
    event_intercept_uh = float(coeffs[1])
    event_intercepts = {
        'SB': intercept,
        'UH': intercept + event_intercept_uh
    }

    # Translate centered diameter coefficients into raw polynomial coefficients
    b1 = float(coeffs[2])
    b2 = float(coeffs[3])
    b1_uh = float(coeffs[4])
    b2_uh = float(coeffs[5])
    c0_sb = intercept - (b1 * diameter_center) + (b2 * (diameter_center ** 2))
    c1_sb = b1 - (2.0 * b2 * diameter_center)
    c2_sb = b2
    c0_uh = (intercept + event_intercept_uh) - ((b1 + b1_uh) * diameter_center) + ((b2 + b2_uh) * (diameter_center ** 2))
    c1_uh = (b1 + b1_uh) - (2.0 * (b2 + b2_uh) * diameter_center)
    c2_uh = (b2 + b2_uh)

    diameter_curves = {
        'SB': {
            'coefficients': [c0_sb, c1_sb, c2_sb],
            'r_squared': float(r_squared),
            'sample_count': len(results_df[results_df['event'].str.upper() == 'SB']),
            'diameter_range': (
                float(results_df['size_mm'].min()),
                float(results_df['size_mm'].max())
            ),
            'anchored': False
        },
        'UH': {
            'coefficients': [c0_uh, c1_uh, c2_uh],
            'r_squared': float(r_squared),
            'sample_count': len(results_df[results_df['event'].str.upper() == 'UH']),
            'diameter_range': (
                float(results_df['size_mm'].min()),
                float(results_df['size_mm'].max())
            ),
            'anchored': False
        }
    }

    model = {
        'event_intercepts': event_intercepts,
        'diameter_curves': diameter_curves,
        'hardness_coefficient': float(coeffs[6]),
        'selection_coefficient': float(coeffs[7]),
        'competitor_effects': competitor_effects,
        'competitor_std_devs': competitor_std_devs,
        'global_std_dev': global_std_dev,
        'sample_count': len(results_df),
        'r_squared': float(r_squared),
        'fitted_date': datetime.now(),
        'events': list(events),
        'coefficients': {
            'intercept': intercept,
            'event_intercept_uh': event_intercept_uh,
            'diameter_linear': b1,
            'diameter_quadratic': b2,
            'diameter_linear_uh': b1_uh,
            'diameter_quadratic_uh': b2_uh
        },
        'centering': {
            'diameter_center': diameter_center,
            'hardness_center': hardness_center,
            'selection_center': selection_center
        }
    }

    return model


def _get_default_hierarchical_model() -> Dict[str, any]:
    """Return default model structure when insufficient data."""
    return {
        'event_intercepts': {'SB': 3.0, 'UH': 3.2},
        'diameter_curves': {
            'SB': {'coefficients': [3.0, 0.002, 0.0], 'r_squared': 0.0, 'sample_count': 0, 'diameter_range': (225, 350), 'anchored': False},
            'UH': {'coefficients': [3.2, 0.002, 0.0], 'r_squared': 0.0, 'sample_count': 0, 'diameter_range': (225, 350), 'anchored': False}
        },
        'hardness_coefficient': 0.3,
        'selection_coefficient': -0.002,
        'competitor_effects': {},
        'competitor_std_devs': {},
        'global_std_dev': 3.0,
        'sample_count': 0,
        'r_squared': 0.0,
        'fitted_date': datetime.now(),
        'events': ['SB', 'UH'],
        'coefficients': {
            'intercept': 3.0,
            'event_intercept_uh': 0.2,
            'diameter_linear': 0.002,
            'diameter_quadratic': 0.0,
            'diameter_linear_uh': 0.0,
            'diameter_quadratic_uh': 0.0
        },
        'centering': {
            'diameter_center': 300.0,
            'hardness_center': 1.0,
            'selection_center': baseline_v2_config.SELECTION_BIAS_DEFAULT_DIAMETER
        }
    }


# ============================================================================
# PHASE 3: HYBRID BASELINE V2 - CONVERGENCE CALIBRATION LAYER
# ============================================================================

def group_wise_bias_correction(
    predictions_dict: Dict[str, float],
    diameter: float,
    event_code: str,
    results_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Apply group-wise bias correction by event/diameter bin.

    Adjusts predictions to eliminate systematic bias within diameter bins,
    ensuring no structural advantage/disadvantage based on wood size.

    Args:
        predictions_dict: {competitor_name: predicted_time}
        diameter: Target diameter in mm
        event_code: Event type (SB/UH)
        results_df: Historical results for bias estimation

    Returns:
        Corrected predictions dictionary
    """
    if not predictions_dict or results_df is None or results_df.empty:
        return predictions_dict

    # Standardize if needed
    if 'raw_time' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    # Determine diameter bin (±25mm)
    diameter_min = diameter - 25
    diameter_max = diameter + 25

    # Get historical data for this diameter bin and event
    event_match = results_df['event'].str.upper() == event_code.upper()
    diameter_match = (results_df['size_mm'] >= diameter_min) & (results_df['size_mm'] <= diameter_max)

    bin_data = results_df[event_match & diameter_match]

    if len(bin_data) < baseline_v2_config.BIAS_CORRECTION_MIN_SAMPLES:
        # Insufficient data for bias correction
        return predictions_dict

    # Calculate historical mean for this bin
    historical_mean = float(bin_data['raw_time'].mean())

    # Calculate current prediction mean
    predicted_mean = float(np.mean(list(predictions_dict.values())))

    # Calculate bias (predicted - historical)
    bias = predicted_mean - historical_mean

    # Only correct significant bias (>1 second)
    if abs(bias) < baseline_v2_config.BIAS_CORRECTION_THRESHOLD_SECONDS:
        return predictions_dict

    # Apply correction: subtract bias from all predictions
    corrected = {
        comp: max(data_req.MIN_VALID_TIME_SECONDS, pred - bias)
        for comp, pred in predictions_dict.items()
    }

    return corrected


def apply_soft_constraints(
    predictions_dict: Dict[str, float],
    results_df: pd.DataFrame,
    event_code: str,
    min_quantile: float = baseline_v2_config.SOFT_CONSTRAINT_QUANTILE
) -> Dict[str, float]:
    """
    Apply soft constraints to prevent under-prediction of slowest competitors.

    Ensures no systematic bias against slower competitors by enforcing
    a floor based on historical minimums.

    Args:
        predictions_dict: {competitor_name: predicted_time}
        results_df: Historical results for floor estimation
        event_code: Event type (SB/UH)
        min_quantile: Quantile threshold for floor (default 0.90 = 90th percentile)

    Returns:
        Constrained predictions dictionary
    """
    if not predictions_dict or results_df is None or results_df.empty:
        return predictions_dict

    # Standardize if needed
    if 'raw_time' not in results_df.columns:
        results_df, _ = standardize_results_data(results_df)

    # Get historical data for this event
    event_data = results_df[results_df['event'].str.upper() == event_code.upper()]

    if len(event_data) < 10:
        return predictions_dict

    # Calculate floor: 90th percentile of historical times (slowest 10%)
    historical_floor = float(event_data['raw_time'].quantile(min_quantile))

    # Find slowest predicted time
    slowest_predicted = max(predictions_dict.values())

    # Check if slowest prediction is unrealistically low
    if slowest_predicted < historical_floor * baseline_v2_config.SOFT_CONSTRAINT_FLOOR_MULTIPLIER:
        # Boost slowest predictions proportionally
        boost_factor = (historical_floor * 0.95) / slowest_predicted

        # Only boost predictions in top 10% (slowest competitors)
        percentile_90 = np.percentile(list(predictions_dict.values()), 90)

        corrected = {}
        for comp, pred in predictions_dict.items():
            if pred >= percentile_90:
                # Boost slow predictions
                corrected[comp] = pred * boost_factor
            else:
                # Leave fast predictions unchanged
                corrected[comp] = pred

        return corrected

    return predictions_dict


def apply_convergence_adjustment(
    predictions_dict: Dict[str, float],
    diameter: float,
    event_code: str,
    target_spread: float = baseline_v2_config.TARGET_FINISH_TIME_SPREAD_SECONDS,
    preserve_ranking: bool = baseline_v2_config.CONVERGENCE_PRESERVE_RANKING
) -> Dict[str, float]:
    """
    Post-process predictions to minimize finish-time spread for handicapping.

    This is the KILLER FEATURE for handicapping: directly optimizes predictions
    to minimize spread while preserving accuracy and competitive fairness.

    Args:
        predictions_dict: {competitor_name: predicted_time}
        diameter: Target diameter in mm (for context)
        event_code: Event type (SB/UH)
        target_spread: Target finish-time spread in seconds (default 2.0s)
        preserve_ranking: If True, maintains relative skill ordering (default True)

    Returns:
        Calibrated predictions dictionary optimized for handicapping

    Example:
        Original predictions: [20.0s, 25.0s, 30.0s, 40.0s]
        Spread: 20s (too wide for handicapping)

        After convergence adjustment with target_spread=2.0s:
        Calibrated: [26.5s, 27.0s, 27.5s, 28.5s]
        Spread: 2.0s (optimal for handicapping)
        Ranking preserved: fastest still fastest, slowest still slowest
    """
    if not predictions_dict or len(predictions_dict) < 2:
        return predictions_dict

    # Calculate current spread
    times = list(predictions_dict.values())
    current_spread = max(times) - min(times)

    # If spread already meets target, no adjustment needed
    if current_spread <= target_spread:
        return predictions_dict

    # Calculate group mean (anchor point)
    mean_time = float(np.mean(times))

    # Calculate compression ratio
    compression_ratio = target_spread / current_spread if current_spread > 0 else 1.0

    # Apply soft compression toward mean while preserving ranking
    calibrated = {}
    for comp, pred in predictions_dict.items():
        # Calculate deviation from mean
        deviation = pred - mean_time

        if preserve_ranking:
            # Compress deviation but preserve sign (ranking)
            compressed_deviation = deviation * compression_ratio
        else:
            # Full compression (equal predictions)
            compressed_deviation = 0.0

        # Calibrated time = mean + compressed deviation
        calibrated_time = mean_time + compressed_deviation

        # Floor at 10s (minimum valid time)
        calibrated[comp] = max(data_req.MIN_VALID_TIME_SECONDS, calibrated_time)

    return calibrated


def calibrate_predictions_for_handicapping(
    predictions_dict: Dict[str, float],
    diameter: float,
    event_code: str,
    results_df: pd.DataFrame,
    target_spread: float = baseline_v2_config.TARGET_FINISH_TIME_SPREAD_SECONDS,
    apply_bias_correction: bool = True,
    apply_constraints: bool = True,
    apply_convergence: bool = True
) -> Tuple[Dict[str, float], Dict[str, any]]:
    """
    Full calibration pipeline for handicap optimization.

    Applies all three calibration layers in sequence:
    1. Group-wise bias correction (eliminate diameter bin bias)
    2. Soft constraints (prevent under-prediction of slowest)
    3. Convergence adjustment (minimize finish-time spread)

    Args:
        predictions_dict: {competitor_name: predicted_time}
        diameter: Target diameter in mm
        event_code: Event type (SB/UH)
        results_df: Historical results for calibration
        target_spread: Target finish-time spread in seconds (default 2.0s)
        apply_bias_correction: Enable group-wise bias correction
        apply_constraints: Enable soft constraints
        apply_convergence: Enable convergence adjustment

    Returns:
        Tuple of (calibrated_predictions, calibration_metadata)

        calibration_metadata contains:
        - original_spread: Spread before calibration
        - calibrated_spread: Spread after calibration
        - bias_correction_applied: Boolean
        - constraints_applied: Boolean
        - convergence_applied: Boolean
        - compression_ratio: Final spread / original spread
    """
    if not predictions_dict:
        return predictions_dict, {'error': 'empty predictions'}

    # Record original state
    original_times = list(predictions_dict.values())
    original_spread = max(original_times) - min(original_times) if len(original_times) > 1 else 0.0

    calibrated = predictions_dict.copy()

    # Step 1: Group-wise bias correction
    bias_correction_applied = False
    if apply_bias_correction and results_df is not None:
        calibrated_after_bias = group_wise_bias_correction(
            calibrated, diameter, event_code, results_df
        )
        if calibrated_after_bias != calibrated:
            calibrated = calibrated_after_bias
            bias_correction_applied = True

    # Step 2: Soft constraints
    constraints_applied = False
    if apply_constraints and results_df is not None:
        calibrated_after_constraints = apply_soft_constraints(
            calibrated, results_df, event_code
        )
        if calibrated_after_constraints != calibrated:
            calibrated = calibrated_after_constraints
            constraints_applied = True

    # Step 3: Convergence adjustment
    convergence_applied = False
    if apply_convergence:
        calibrated_after_convergence = apply_convergence_adjustment(
            calibrated, diameter, event_code, target_spread
        )
        if calibrated_after_convergence != calibrated:
            calibrated = calibrated_after_convergence
            convergence_applied = True

    # Calculate final state
    calibrated_times = list(calibrated.values())
    calibrated_spread = max(calibrated_times) - min(calibrated_times) if len(calibrated_times) > 1 else 0.0
    compression_ratio = calibrated_spread / original_spread if original_spread > 0 else 1.0

    metadata = {
        'original_spread': round(original_spread, 2),
        'calibrated_spread': round(calibrated_spread, 2),
        'bias_correction_applied': bias_correction_applied,
        'constraints_applied': constraints_applied,
        'convergence_applied': convergence_applied,
        'compression_ratio': round(compression_ratio, 3),
        'target_spread': target_spread
    }

    return calibrated, metadata


# ============================================================================
# PHASE 4: HYBRID BASELINE V2 - MODEL CACHING & PREDICTION INTERFACE
# ============================================================================

# Global cache for Baseline V2 model
_baseline_v2_cache: Optional[Dict[str, any]] = None
_cache_last_updated: Optional[datetime] = None


def fit_and_cache_baseline_v2_model(
    results_df: pd.DataFrame,
    wood_df: pd.DataFrame,
    force_refit: bool = False
) -> Dict[str, any]:
    """
    Fit and cache the complete Baseline V2 hybrid model.

    This is the precomputation layer that builds:
    - Wood hardness index (Phase 1)
    - Adaptive half-lives (Phase 1)
    - Hierarchical regression model (Phase 2)

    Model is cached globally and reused until data changes.

    Args:
        results_df: Historical results DataFrame
        wood_df: Wood properties DataFrame
        force_refit: If True, ignore cache and refit model

    Returns:
        Dictionary containing:
        - hardness_index: {speciesID: composite_index}
        - adaptive_half_lives: {competitor_name: half_life_days}
        - hierarchical_model: Fitted model parameters
        - fitted_date: When model was fitted
        - cache_version: Version identifier
    """
    global _baseline_v2_cache, _cache_last_updated

    from config import baseline_v2_config
    from woodchopping.data import load_and_clean_results, fit_wood_hardness_index, calculate_adaptive_half_lives

    # Check if cache is valid
    if not force_refit and _baseline_v2_cache is not None and baseline_v2_config.ENABLE_MODEL_CACHE:
        # Cache hit
        return _baseline_v2_cache

    # Cache miss or forced refit - build new model
    print("[Baseline V2] Fitting hybrid model...")

    # Phase 1: Preprocessing
    cleaned_results = load_and_clean_results(results_df)

    hardness_index = fit_wood_hardness_index(cleaned_results, wood_df)
    adaptive_half_lives = calculate_adaptive_half_lives(cleaned_results)

    # Phase 2: Hierarchical model fitting
    hierarchical_model = fit_hierarchical_regression(
        cleaned_results,
        wood_df,
        hardness_index,
        adaptive_half_lives,
        event_code=None  # Fit for all events
    )

    # Build cache
    cache = {
        'hardness_index': hardness_index,
        'adaptive_half_lives': adaptive_half_lives,
        'hierarchical_model': hierarchical_model,
        'fitted_date': datetime.now(),
        'cache_version': 'v2.0',
        'sample_count': len(cleaned_results),
        'results_df': cleaned_results  # Store cleaned data for calibration
    }

    # Update global cache
    _baseline_v2_cache = cache
    _cache_last_updated = datetime.now()

    print(f"[Baseline V2] Model fitted successfully. Sample count: {cache['sample_count']}")

    return cache


def invalidate_baseline_v2_cache():
    """Invalidate the global Baseline V2 model cache."""
    global _baseline_v2_cache, _cache_last_updated
    _baseline_v2_cache = None
    _cache_last_updated = None
    print("[Baseline V2] Cache invalidated")


def predict_baseline_v2_hybrid(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: Optional[float],
    event_code: str,
    results_df: pd.DataFrame,
    wood_df: Optional[pd.DataFrame] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    enable_calibration: bool = True
) -> Tuple[Optional[float], str, str, Optional[Dict[str, any]]]:
    """
    Main prediction interface for Baseline V2 Hybrid model.

    Combines all phases:
    - Phase 1: Data preprocessing with wood hardness index & adaptive decay
    - Phase 2: Hierarchical regression with selection bias correction
    - Phase 3: Convergence calibration for handicapping optimization

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (0-10), None defaults to 5
        event_code: Event type (SB/UH)
        results_df: Historical results DataFrame
        wood_df: Wood properties DataFrame (optional)
        tournament_results: Same-tournament times for 97% weighting (optional)
        enable_calibration: Apply convergence calibration (default True)

    Returns:
        Tuple of (predicted_time, confidence, explanation, metadata)

        metadata contains:
        - std_dev: Competitor-specific standard deviation
        - consistency_rating: VERY HIGH / HIGH / MODERATE / LOW
        - median_diameter: Competitor's median diameter choice
        - hardness_index: Wood hardness index value
        - adaptive_half_life: Competitor's time-decay half-life
        - calibration_metadata: Convergence calibration details (if enabled)
        - prediction_interval: (lower, upper) 95% confidence interval

    Example:
        >>> time, conf, expl, meta = predict_baseline_v2_hybrid(
        ...     "John Smith", "S01", 300, 5, "SB", results_df
        ... )
        >>> print(f"Predicted: {time:.1f}s ({conf})")
        >>> print(f"Consistency: {meta['consistency_rating']}")
        >>> print(f"95% interval: {meta['prediction_interval']}")
    """
    from config import baseline_v2_config
    from woodchopping.data import load_wood_data

    if wood_df is None:
        wood_df = load_wood_data()

    # Build or retrieve cached model
    cache = fit_and_cache_baseline_v2_model(results_df, wood_df)

    hardness_index = cache['hardness_index']
    adaptive_half_lives = cache['adaptive_half_lives']
    hierarchical_model = cache['hierarchical_model']
    cleaned_results = cache['results_df']

    # Tournament result weighting (97/3) - same as V1
    if tournament_results and competitor_name in tournament_results:
        tournament_time = tournament_results[competitor_name]

        # Get fallback prediction for 3% weighting
        fallback_pred, _, _, _ = predict_baseline_v2_hybrid(
            competitor_name, species, diameter, quality, event_code,
            results_df, wood_df, tournament_results=None, enable_calibration=False
        )

        if fallback_pred is not None:
            # 97% tournament, 3% historical
            predicted_time = (tournament_time * 0.97) + (fallback_pred * 0.03)
            confidence = "VERY HIGH"
            explanation = f"Tournament result ({tournament_time:.1f}s) weighted 97%, historical baseline 3%"

            # Get metadata
            std_dev, consistency = estimate_competitor_std_dev(
                competitor_name, event_code, cleaned_results,
                min_std_dev=baseline_v2_config.MIN_STD_DEV_SECONDS,
                max_std_dev=baseline_v2_config.MAX_STD_DEV_SECONDS
            )

            metadata = {
                'std_dev': std_dev,
                'consistency_rating': consistency,
                'tournament_weighted': True,
                'prediction_interval': (
                    max(data_req.MIN_VALID_TIME_SECONDS, predicted_time - 1.96 * std_dev),
                    predicted_time + 1.96 * std_dev
                )
            }

            return predicted_time, confidence, explanation, metadata

    # Get competitor features
    median_diam = get_competitor_median_diameter(competitor_name, event_code, cleaned_results)

    hardness_idx = hardness_index.get(species, 1.0)

    half_life = adaptive_half_lives.get(competitor_name, baseline_v2_config.HALF_LIFE_MODERATE_DAYS)

    std_dev, consistency = estimate_competitor_std_dev(
        competitor_name, event_code, cleaned_results,
        min_std_dev=baseline_v2_config.MIN_STD_DEV_SECONDS,
        max_std_dev=baseline_v2_config.MAX_STD_DEV_SECONDS
    )

    # Get competitor historical data with adaptive weighting
    historical_data, data_source, norm_meta = get_competitor_historical_times_normalized(
        competitor_name, species, diameter, event_code, cleaned_results,
        return_weights=True, wood_df=wood_df
    )

    model_ready = hierarchical_model.get('sample_count', 0) >= baseline_v2_config.MIN_DATA_FOR_HIERARCHICAL_MODEL
    if model_ready:
        coeffs = hierarchical_model.get('coefficients', {})
        centering = hierarchical_model.get('centering', {})

        intercept = float(coeffs.get('intercept', 3.0))
        event_intercept_uh = float(coeffs.get('event_intercept_uh', 0.0))
        diam_lin = float(coeffs.get('diameter_linear', 0.0))
        diam_quad = float(coeffs.get('diameter_quadratic', 0.0))
        diam_lin_uh = float(coeffs.get('diameter_linear_uh', 0.0))
        diam_quad_uh = float(coeffs.get('diameter_quadratic_uh', 0.0))

        diameter_center = float(centering.get('diameter_center', 300.0))
        hardness_center = float(centering.get('hardness_center', 1.0))
        selection_center = float(centering.get('selection_center', baseline_v2_config.SELECTION_BIAS_DEFAULT_DIAMETER))

        event_is_uh = 1.0 if event_code.upper() == 'UH' else 0.0
        diameter_for_model = float(median_diam) if median_diam is not None else float(diameter)
        d = diameter_for_model - diameter_center
        d2 = d ** 2

        hardness_centered = hardness_idx - hardness_center
        selection_centered = median_diam - selection_center

        log_pred = (
            intercept +
            (event_intercept_uh * event_is_uh) +
            (diam_lin * d) +
            (diam_quad * d2) +
            (diam_lin_uh * event_is_uh * d) +
            (diam_quad_uh * event_is_uh * d2) +
            (hierarchical_model.get('hardness_coefficient', 0.0) * hardness_centered) +
            (hierarchical_model.get('selection_coefficient', 0.0) * selection_centered)
        )

        comp_key = str(competitor_name).strip().lower()
        comp_effect = hierarchical_model.get('competitor_effects', {}).get(comp_key, 0.0)
        log_pred += float(comp_effect)

        baseline = float(np.exp(log_pred))
        explanation = "Hierarchical regression (skill at median diameter + wood/selection + competitor effect)"

        # Enforce realistic diameter scaling using calibrated power-law (selection bias can invert diameter trend)
        if diameter is not None and median_diam is not None and float(diameter) != float(median_diam):
            exponent = get_event_scaling_exponent(cleaned_results, event_code)
            scaled, metadata = scale_time(
                baseline,
                float(median_diam),
                float(diameter),
                exponent=exponent
            )
            baseline = float(scaled)
            if metadata.warning_message:
                explanation += f" + {metadata.warning_message} (exp {exponent:.2f})"
    else:
        baseline = None
        explanation = "No fitted hierarchical model"

    # Compute effective sample size for confidence
    effective_n = 0.0
    if historical_data:
        _, _, effective_n = compute_robust_weighted_mean(historical_data)

    # Determine confidence based on weighted samples and std_dev
    if effective_n >= baseline_v2_config.CONFIDENCE_VERY_HIGH_MIN_WEIGHTED_SAMPLES and std_dev <= baseline_v2_config.CONFIDENCE_VERY_HIGH_MAX_STD_DEV:
        confidence = "VERY HIGH"
    elif effective_n >= baseline_v2_config.CONFIDENCE_HIGH_MIN_WEIGHTED_SAMPLES and std_dev <= baseline_v2_config.CONFIDENCE_HIGH_MAX_STD_DEV:
        confidence = "HIGH"
    elif effective_n >= baseline_v2_config.CONFIDENCE_MEDIUM_MIN_WEIGHTED_SAMPLES:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    if model_ready and effective_n > 0:
        explanation += f" [eff_n {effective_n:.1f}]"

    if baseline is None:
        # Fallback to event baseline if regression unavailable
        baseline, baseline_source = get_event_baseline_flexible(
            species, diameter, event_code, cleaned_results, wood_df=wood_df
        )
        if baseline is not None:
            explanation = f"Event baseline ({baseline_source})"
        else:
            return None, "LOW", "No prediction possible", None

    # Blend hierarchical prediction with competitor history (when available)
    if historical_data:
        hist_mean, _, _ = compute_robust_weighted_mean(historical_data)
        event_baseline, event_source = get_event_baseline_flexible(
            species, diameter, event_code, cleaned_results, wood_df=wood_df
        )
        if hist_mean is not None and event_baseline is not None:
            # Avoid over-shrinking slow competitors toward the event mean
            if hist_mean > event_baseline * 1.35:
                explanation += " + history preserved (slow-competitor safeguard)"
            else:
                hist_mean = apply_shrinkage(hist_mean, effective_n, event_baseline)
        if hist_mean is not None:
            hist_count = len(historical_data)
            if hist_count >= 3:
                hist_weight = 0.7
            else:
                hist_weight = 0.6
            baseline = (hist_weight * hist_mean) + ((1.0 - hist_weight) * baseline)
            explanation += f" + blended history ({hist_count} results, w={hist_weight:.1f})"

    # Apply quality adjustment
    quality_val = int(quality) if quality is not None and not pd.isna(quality) else 5
    quality_val = max(1, min(10, quality_val))

    if quality_val != 5:
        quality_offset = quality_val - 5
        quality_factor = 1.0 + (quality_offset * 0.02)
        baseline = baseline * quality_factor

        adjustment_pct = (quality_factor - 1.0) * 100
        if quality_val < 5:
            explanation += f" [Quality {quality_val}/10: softer, {adjustment_pct:+.0f}%]"
        else:
            explanation += f" [Quality {quality_val}/10: harder, {adjustment_pct:+.0f}%]"

    # Downgrade confidence if heavy normalization was needed
    if norm_meta.get('max_diameter_diff', 0.0) > 25 or norm_meta.get('species_normalized', False):
        if confidence == "VERY HIGH":
            confidence = "HIGH"
        elif confidence == "HIGH":
            confidence = "MEDIUM"
        elif confidence == "MEDIUM":
            confidence = "LOW"
        explanation += " [Normalized sizes/species]"

    # Build metadata
    metadata = {
        'std_dev': std_dev,
        'consistency_rating': consistency,
        'median_diameter': median_diam,
        'hardness_index': hardness_idx,
        'adaptive_half_life': half_life,
        'effective_samples': effective_n if 'effective_n' in locals() else 0,
        'tournament_weighted': False,
        'prediction_interval': (
            max(data_req.MIN_VALID_TIME_SECONDS, baseline - 1.96 * std_dev),
            baseline + 1.96 * std_dev
        )
    }

    predicted_time = baseline

    # Phase 3: Convergence calibration (optional, for batch handicapping)
    if enable_calibration:
        # Note: Calibration requires all competitor predictions
        # This is typically done at the batch level in prediction_aggregator
        # Individual predictions skip calibration
        metadata['calibration_note'] = "Calibration skipped (requires batch predictions)"

    return predicted_time, confidence, explanation, metadata
