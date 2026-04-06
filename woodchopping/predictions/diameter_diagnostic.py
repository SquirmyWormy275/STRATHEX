"""
Diameter monotonicity diagnostic for baseline predictions.

Checks that predicted times are non-decreasing as diameter increases.
"""

from typing import Dict, List, Optional

import pandas as pd

from woodchopping.data import load_results_df, load_wood_data, standardize_results_data
from woodchopping.predictions.baseline import predict_baseline_v2_hybrid


def run_diameter_monotonicity_diagnostic(
    results_df: Optional[pd.DataFrame] = None,
    wood_df: Optional[pd.DataFrame] = None,
    diameters: Optional[List[int]] = None,
    event_filter: Optional[str] = None,
    min_results: int = 3,
    tolerance_seconds: float = 0.25,
    sample_limit: Optional[int] = None,
) -> Dict[str, any]:
    """
    Diagnose diameter monotonicity for Baseline V2 predictions.

    Args:
        results_df: Historical results (optional, loaded if None)
        wood_df: Wood properties (optional, loaded if None)
        diameters: List of diameters to test (default: STRATHEX standard diameters)
        event_filter: 'SB' or 'UH' to restrict, or None for both
        min_results: Minimum history rows per competitor+event to include
        tolerance_seconds: Allowed small non-monotonic wiggle
        sample_limit: Optional cap on number of competitors per event

    Returns:
        Dict with summary and violations.
    """
    if results_df is None:
        results_df = load_results_df()
    if wood_df is None:
        wood_df = load_wood_data()

    if results_df is None or results_df.empty:
        return {"status": "ERROR", "message": "No results data available"}

    results_df, _ = standardize_results_data(results_df)

    if diameters is None:
        diameters = [225, 250, 275, 300, 325, 350]

    diameters = sorted(set(int(d) for d in diameters))

    if event_filter:
        event_filter = event_filter.strip().upper()

    violations = []
    total_checked = 0

    grouped = results_df.groupby(["competitor_name", "event"])
    for (competitor, event), group in grouped:
        event_code = str(event).strip().upper()
        if event_filter and event_code != event_filter:
            continue
        if len(group) < min_results:
            continue

        species_counts = group["species"].dropna().astype(str).str.strip().value_counts()
        if species_counts.empty:
            continue
        species = species_counts.index[0]

        preds = []
        for diameter in diameters:
            pred, conf, expl, meta = predict_baseline_v2_hybrid(
                competitor_name=competitor,
                species=species,
                diameter=float(diameter),
                quality=5,
                event_code=event_code,
                results_df=results_df,
                wood_df=wood_df,
                tournament_results=None,
                enable_calibration=False,
            )
            if pred is None:
                preds = []
                break
            preds.append((diameter, float(pred)))

        if not preds:
            continue

        total_checked += 1
        if sample_limit and total_checked >= sample_limit:
            break

        # Check non-decreasing times as diameter increases
        last_d, last_t = preds[0]
        for d, t in preds[1:]:
            if t + tolerance_seconds < last_t:
                violations.append(
                    {
                        "competitor": competitor,
                        "event": event_code,
                        "species": species,
                        "diameter_prev": last_d,
                        "time_prev": last_t,
                        "diameter": d,
                        "time": t,
                        "delta": t - last_t,
                    }
                )
                break
            last_d, last_t = d, t

    summary = {
        "status": "OK",
        "total_checked": total_checked,
        "violations": violations,
        "violation_count": len(violations),
        "tolerance_seconds": tolerance_seconds,
        "diameters": diameters,
        "event_filter": event_filter or "ALL",
    }

    print("\nDIAMETER MONOTONICITY DIAGNOSTIC")
    print("-" * 70)
    print(f"Checked: {total_checked} competitor-event pairs")
    print(f"Diameters: {diameters}")
    print(f"Tolerance: {tolerance_seconds:.2f}s")
    print(f"Violations: {len(violations)}")

    if violations:
        print("\nSample violations (first 10):")
        for v in violations[:10]:
            print(
                f"  {v['competitor']} [{v['event']}] {v['species']} "
                f"{v['diameter_prev']}mm {v['time_prev']:.2f}s -> "
                f"{v['diameter']}mm {v['time']:.2f}s (delta {v['delta']:+.2f}s)"
            )
    else:
        print("No monotonicity violations detected.")

    print("-" * 70)

    return summary
