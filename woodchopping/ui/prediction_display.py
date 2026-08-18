"""Judge-facing STRATHMARK v2 prediction and handicap explanations."""

from __future__ import annotations

from typing import Any, Dict, List


def _interval_text(result: Dict[str, Any]) -> str:
    interval = result.get("prediction_interval") or {}
    lower = interval.get("lower")
    upper = interval.get("upper")
    if lower is None or upper is None:
        return "unavailable"
    return f"{lower:.1f}-{upper:.1f}s"


def display_basic_prediction_table(handicap_results: List[Dict], wood_selection: Dict) -> None:
    """Display marks, v2 predictions, calibrated intervals, and health state."""
    print("\n" + "=" * 100)
    print(f"  STRATHMARK V2 HANDICAP MARKS - {wood_selection.get('event', 'Unknown Event')}")
    print("=" * 100)
    print(
        f"{'Competitor':<25} {'Mark':>4} {'Pred':>8} {'90% interval':>19} {'Confidence':<11} {'Method':<13} {'Status'}"
    )
    print("-" * 100)
    for result in handicap_results:
        status = "DEGRADED" if result.get("degraded") else "ready"
        if result.get("warnings"):
            status = f"{status}; warning"
        print(
            f"{result['name'][:24]:<25} {result['mark']:>4} {result['predicted_time']:>7.1f}s "
            f"{_interval_text(result):>19} {str(result.get('confidence') or 'n/a'):<11} "
            f"{str(result.get('method_used') or 'n/a'):<13} {status}"
        )
    print("=" * 100)
    print("Wood quality and same-tournament times are context, not numeric v2 prediction inputs.\n")


def display_comprehensive_prediction_analysis(
    handicap_results: List[Dict],
    wood_selection: Dict,
    ml_training_info: Dict | None = None,
) -> None:
    """Display v2 evidence, provenance, uncertainty, and optimizer metadata."""
    del wood_selection, ml_training_info
    print("\n" + "=" * 100)
    print("STRATHMARK V2 PREDICTION EVIDENCE")
    print("=" * 100)
    print("One prior-only hierarchical core predicts the field; a joint optimizer assigns marks.")
    print("Forecast intervals and race-performance spread are separate quantities.\n")
    print(f"{'Competitor':<24} {'Pred':>7} {'90% interval':>19} {'Std':>7} {'Method':<13} {'Engine':<8} {'State'}")
    print("-" * 100)
    for result in handicap_results:
        state = "DEGRADED" if result.get("degraded") else "ready"
        print(
            f"{result['name'][:23]:<24} {result['predicted_time']:>6.1f}s "
            f"{_interval_text(result):>19} {result.get('performance_std_dev', 3.0):>6.1f}s "
            f"{result.get('method_used', 'Unknown'):<13} "
            f"{str(result.get('engine_version') or 'n/a'):<8} {state}"
        )
        print(f"  Evidence cutoff: {result.get('evidence_cutoff') or 'not reported'}")
        print(f"  Optimizer: {result.get('optimizer') or 'not reported'}")
        for warning in result.get("warnings", []):
            print(f"  WARNING: {warning}")
        ignored = result.get("ignored_factors", [])
        if ignored:
            print(f"  Ignored compatibility inputs: {', '.join(ignored)}")
    print("=" * 100)


def display_handicap_calculation_explanation() -> None:
    """Explain the live v2 calculation in plain operator language."""
    print("\n" + "=" * 70)
    print("HOW STRATHEX 7 CALCULATES HANDICAPS")
    print("=" * 70)
    print(
        "1. STRATHEX sends stable competitor IDs, dated history, wood, event, "
        "and one exclusive evidence cutoff to STRATHMARK v2."
    )
    print("2. STRATHMARK's hierarchical prior predicts every competitor under one immutable model snapshot.")
    print("3. A deterministic joint optimizer assigns legal marks for the whole field.")
    print("4. STRATHEX displays the forecast interval, performance spread, provenance, warnings, and engine version.")
    print("5. Manual judge adjustments remain explicit and are recorded separately.")
    print("\nSame-day results and wood quality are retained as context but do not change v2's numeric prediction.")
    print("Excel is the judge-canonical result record; ResultStore is a best-effort derived history store.")
    print("=" * 70)
