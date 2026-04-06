"""
Prediction Accuracy Tracking Module (B1)

Tracks prediction accuracy by comparing predicted times vs actual times,
calculating error metrics (MAE, MPE, RMSE), and identifying which prediction
methods perform best.
"""

from datetime import datetime
from typing import Dict, List

import numpy as np


def analyze_prediction_accuracy(round_state: Dict) -> Dict:
    """
    Analyze prediction accuracy for a completed round.

    Args:
        round_state: Round object with:
            - handicap_results: List of dicts with predicted times
            - results: Dict mapping competitor names to actual times
            - round_name: Name of the round (e.g., "Heat 1")

    Returns:
        Dictionary with:
        - mae: Mean Absolute Error
        - mpe: Mean Percentage Error
        - rmse: Root Mean Square Error
        - bias: Average prediction error (positive = underestimating)
        - accuracy_rating: EXCELLENT/VERY GOOD/GOOD/FAIR/POOR
        - per_competitor: List of per-competitor error stats
        - per_method: List of per-method accuracy stats (if available)
        - insights: List of human-readable insight strings
    """

    # Extract data
    handicap_results = round_state.get("handicap_results", [])
    actual_results = round_state.get("results", {})
    round_name = round_state.get("round_name", "Unknown Round")

    # Build comparison data
    comparisons = []
    for handicap_entry in handicap_results:
        name = handicap_entry["name"]
        predicted_time = handicap_entry.get("predicted_time")

        if name in actual_results and predicted_time is not None:
            actual_time = actual_results[name]

            # Skip DNF or invalid times
            if actual_time is None or actual_time <= 0:
                continue

            comparisons.append(
                {
                    "name": name,
                    "predicted": predicted_time,
                    "actual": actual_time,
                    "method": handicap_entry.get("prediction_method", "Unknown"),
                }
            )

    if not comparisons:
        return {
            "mae": None,
            "mpe": None,
            "rmse": None,
            "bias": None,
            "accuracy_rating": "NO DATA",
            "per_competitor": [],
            "per_method": [],
            "insights": ["No valid predictions to analyze"],
        }

    # Calculate per-competitor errors
    per_competitor = []
    absolute_errors = []
    percentage_errors = []
    squared_errors = []
    raw_errors = []

    for comp in comparisons:
        error = comp["actual"] - comp["predicted"]
        abs_error = abs(error)
        pct_error = (error / comp["predicted"]) * 100 if comp["predicted"] > 0 else 0
        sq_error = error**2

        per_competitor.append(
            {
                "name": comp["name"],
                "predicted": float(comp["predicted"]),
                "actual": float(comp["actual"]),
                "error": float(error),
                "abs_error": float(abs_error),
                "pct_error": float(pct_error),
                "method": comp["method"],
            }
        )

        absolute_errors.append(abs_error)
        percentage_errors.append(pct_error)
        squared_errors.append(sq_error)
        raw_errors.append(error)

    # Calculate aggregate metrics
    mae = np.mean(absolute_errors)
    mpe = np.mean(percentage_errors)
    rmse = np.sqrt(np.mean(squared_errors))
    bias = np.mean(raw_errors)

    # Get accuracy rating
    accuracy_rating = _get_accuracy_rating(mae)

    # Sort per_competitor by absolute error (largest errors first for reporting)
    per_competitor_sorted = sorted(per_competitor, key=lambda x: x["abs_error"], reverse=True)

    # Mark largest and smallest errors
    if len(per_competitor_sorted) > 0:
        per_competitor_sorted[0]["flag"] = "LARGEST ERROR"
        # Find most accurate (smallest error)
        most_accurate = min(per_competitor_sorted, key=lambda x: x["abs_error"])
        for comp in per_competitor_sorted:
            if comp["name"] == most_accurate["name"]:
                comp["flag"] = "MOST ACCURATE"
                break

    # Per-method breakdown (if prediction methods are tracked)
    per_method = _calculate_per_method_accuracy(comparisons)

    # Generate insights
    insights = _generate_insights(mae, mpe, bias, per_competitor_sorted, per_method)

    return {
        "mae": float(mae),
        "mpe": float(mpe),
        "rmse": float(rmse),
        "bias": float(bias),
        "accuracy_rating": accuracy_rating,
        "per_competitor": per_competitor_sorted,
        "per_method": per_method,
        "insights": insights,
        "round_name": round_name,
        "timestamp": datetime.now().isoformat(),
    }


def _get_accuracy_rating(mae: float) -> str:
    """
    Get accuracy rating based on MAE.

    Thresholds:
    - EXCELLENT: MAE < 2.0s
    - VERY GOOD: MAE < 3.0s
    - GOOD: MAE < 4.0s
    - FAIR: MAE < 5.0s
    - POOR: MAE >= 5.0s
    """
    if mae < 2.0:
        return "EXCELLENT"
    elif mae < 3.0:
        return "VERY GOOD"
    elif mae < 4.0:
        return "GOOD"
    elif mae < 5.0:
        return "FAIR"
    else:
        return "POOR"


def _calculate_per_method_accuracy(comparisons: List[Dict]) -> List[Dict]:
    """
    Calculate accuracy statistics per prediction method.

    Args:
        comparisons: List of comparison dicts with 'method', 'predicted', 'actual'

    Returns:
        List of dicts with method, count, and mae
    """
    method_stats = {}

    for comp in comparisons:
        method = comp.get("method", "Unknown")
        error = abs(comp["actual"] - comp["predicted"])

        if method not in method_stats:
            method_stats[method] = {"errors": [], "count": 0}

        method_stats[method]["errors"].append(error)
        method_stats[method]["count"] += 1

    # Calculate MAE per method
    per_method = []
    for method, stats in method_stats.items():
        mae = np.mean(stats["errors"])
        per_method.append({"method": method, "count": stats["count"], "mae": float(mae)})

    # Sort by MAE (best first)
    per_method.sort(key=lambda x: x["mae"])

    # Mark most accurate method
    if len(per_method) > 0:
        per_method[0]["flag"] = "MOST ACCURATE"

    return per_method


def _generate_insights(
    mae: float, mpe: float, bias: float, per_competitor: List[Dict], per_method: List[Dict]
) -> List[str]:
    """
    Generate human-readable insights from accuracy analysis.

    Args:
        mae: Mean absolute error
        mpe: Mean percentage error
        bias: Prediction bias
        per_competitor: Per-competitor stats (sorted by error)
        per_method: Per-method stats

    Returns:
        List of insight strings
    """
    insights = []

    # Overall accuracy assessment
    if mae < 2.0:
        insights.append(f"Overall accuracy is excellent (within {mae:.1f} seconds average)")
    elif mae < 3.0:
        insights.append(f"Overall accuracy is very good (within {mae:.1f} seconds average)")
    elif mae < 4.0:
        insights.append(f"Overall accuracy is good (within {mae:.1f} seconds average)")
    else:
        insights.append(f"Overall accuracy needs improvement ({mae:.1f} seconds average error)")

    # Bias analysis
    if abs(bias) < 0.5:
        insights.append("Predictions are well-calibrated (minimal systematic bias)")
    elif bias > 0.5:
        insights.append(
            f"Slight bias toward underestimating times (+{bias:.1f}s avg) - competitors finishing slower than predicted"
        )
    else:
        insights.append(
            f"Slight bias toward overestimating times ({bias:.1f}s avg) - competitors finishing faster than predicted"
        )

    # Largest error alert
    if len(per_competitor) > 0:
        worst = per_competitor[0]
        if worst["abs_error"] > 3.0:
            insights.append(
                f"{worst['name']}'s time was {worst['error']:+.1f}s from prediction - may need handicap adjustment for next round"
            )

    # Method comparison
    if len(per_method) > 1:
        best_method = per_method[0]
        insights.append(f"{best_method['method']} method performed best this round")

    return insights


def format_prediction_accuracy_report(analysis: Dict) -> str:
    """
    Format prediction accuracy analysis as a text report.

    Args:
        analysis: Dict returned from analyze_prediction_accuracy()

    Returns:
        Formatted text report string
    """
    lines = []

    # Header
    lines.append("╔" + "═" * 68 + "╗")
    lines.append("║" + "PREDICTION ACCURACY REPORT".center(68) + "║")
    lines.append("║" + analysis.get("round_name", "Unknown Round").center(68) + "║")
    lines.append("╚" + "═" * 68 + "╝")
    lines.append("")

    # Overall accuracy
    lines.append("Overall Accuracy:")
    if analysis["mae"] is not None:
        lines.append(f"  Mean Absolute Error (MAE): {analysis['mae']:.1f} seconds")
        lines.append(f"  Mean Percentage Error (MPE): {analysis['mpe']:.1f}%")
        lines.append(f"  Root Mean Square Error (RMSE): {analysis['rmse']:.1f} seconds")
        lines.append(
            f"  Prediction Bias: {analysis['bias']:+.1f} seconds "
            + (
                "(slightly underestimating)"
                if analysis["bias"] > 0
                else "(slightly overestimating)"
                if analysis["bias"] < -0.1
                else "(well-calibrated)"
            )
        )
        lines.append("")
        lines.append(f"Accuracy Rating: {analysis['accuracy_rating']} (MAE < 2.0s)")
    else:
        lines.append("  No data available")

    lines.append("")

    # Per-competitor breakdown
    if analysis["per_competitor"]:
        lines.append("Per-Competitor Breakdown:")
        lines.append("+" + "-" * 22 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 9 + "+")
        lines.append("| Competitor           | Predicted | Actual    | Error     | % Error |")
        lines.append("+" + "-" * 22 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 9 + "+")

        for comp in analysis["per_competitor"]:
            name = comp["name"][:20].ljust(20)
            predicted = f"{comp['predicted']:.1f}s".center(9)
            actual = f"{comp['actual']:.1f}s".center(9)
            error = f"{comp['error']:+.1f}s".center(9)
            pct_error = f"{comp['pct_error']:+.1f}%".center(7)

            flag = f" ? {comp.get('flag', '')}" if "flag" in comp else ""

            lines.append(f"| {name} | {predicted} | {actual} | {error} | {pct_error} |{flag}")

        lines.append("+" + "-" * 22 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 11 + "+" + "-" * 9 + "+")
        lines.append("")

    # Per-method comparison
    if len(analysis.get("per_method", [])) > 1:
        lines.append("Prediction Method Comparison:")
        lines.append("+" + "-" * 17 + "+" + "-" * 13 + "+" + "-" * 19 + "+")
        lines.append("| Method          | Times Used  | Avg Error (MAE)   |")
        lines.append("+" + "-" * 17 + "+" + "-" * 13 + "+" + "-" * 19 + "+")

        for method in analysis["per_method"]:
            method_name = method["method"][:15].ljust(15)
            count = str(method["count"]).center(11)
            mae = f"{method['mae']:.1f}s".center(17)

            flag = f" ? {method.get('flag', '')}" if "flag" in method else ""

            lines.append(f"| {method_name} | {count} | {mae} |{flag}")

        lines.append("+" + "-" * 17 + "+" + "-" * 13 + "+" + "-" * 19 + "+")
        lines.append("")

    # Insights
    if analysis.get("insights"):
        lines.append("Insights:")
        for insight in analysis["insights"]:
            lines.append(f"  - {insight}")
        lines.append("")

    lines.append("[Press Enter to continue]")

    return "\n".join(lines)
