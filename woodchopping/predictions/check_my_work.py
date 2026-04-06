"""
Check My Work - Handicap Validation Summary

Provides judges with a concise validation report before approving handicaps.
Shows key issues, discrepancies, and confidence levels in an easy-to-scan format.
"""

import statistics
from typing import Dict, List


def check_my_work(handicap_results: List[Dict], wood_selection: Dict) -> Dict[str, any]:
    """
    Generate a "Check My Work" validation summary for judges.

    Analyzes handicap results and returns a summary of:
    - Prediction method agreement/disagreement
    - Confidence warnings
    - Diameter scaling alerts
    - Fairness assessment
    - Recommended actions

    Args:
        handicap_results: List of competitor results with predictions
        wood_selection: Wood characteristics dict

    Returns:
        Dict with validation summary and recommendation
    """
    if not handicap_results:
        return {"status": "ERROR", "message": "No handicap results to validate"}

    # Initialize validation tracking
    total_competitors = len(handicap_results)

    # Track issues
    large_discrepancies = []  # Methods disagree >20% or >4s
    low_confidence = []  # Confidence is LOW or VERY LOW
    scaled_predictions = []  # Cross-diameter scaling applied
    no_ml_predictions = []  # ML unavailable
    high_variance_risk = []  # Wide prediction spread

    # Track prediction method usage
    methods_used = {"Baseline": 0, "ML": 0, "LLM": 0, "Baseline (scaled)": 0}

    # Analyze each competitor
    for result in handicap_results:
        name = result["name"]
        predictions = result["predictions"]
        method_used = result.get("method_used", "Unknown")
        confidence = result.get("confidence", "UNKNOWN")

        # Count method usage
        methods_used[method_used] = methods_used.get(method_used, 0) + 1

        # Check confidence
        if confidence in ["LOW", "VERY LOW"]:
            low_confidence.append(
                {
                    "name": name,
                    "confidence": confidence,
                    "reason": predictions.get(method_used.lower().replace(" (scaled)", ""), {}).get(
                        "explanation", "Unknown"
                    ),
                }
            )

        # Check for diameter scaling
        baseline_pred = predictions.get("baseline", {})
        if baseline_pred.get("scaled", False):
            scaled_predictions.append(
                {"name": name, "warning": baseline_pred.get("scaling_warning", "Diameter scaled")}
            )

        # Check if ML unavailable
        if predictions.get("ml", {}).get("time") is None:
            no_ml_predictions.append(name)

        # Check for large discrepancies between methods
        baseline_time = predictions["baseline"]["time"]
        ml_time = predictions["ml"]["time"]
        llm_time = predictions["llm"]["time"]

        # Calculate discrepancies (percent and absolute seconds)
        if baseline_time and ml_time:
            diff_pct = abs((baseline_time - ml_time) / ml_time) * 100
            diff_abs = abs(baseline_time - ml_time)
            if diff_pct > 20 or diff_abs >= 4.0:
                large_discrepancies.append(
                    {
                        "name": name,
                        "baseline": baseline_time,
                        "ml": ml_time,
                        "diff_pct": diff_pct,
                        "diff_abs": diff_abs,
                        "methods": "Baseline vs ML",
                    }
                )

        if baseline_time and llm_time:
            diff_pct = abs((baseline_time - llm_time) / llm_time) * 100
            diff_abs = abs(baseline_time - llm_time)
            if diff_pct > 20 or diff_abs >= 4.0:
                large_discrepancies.append(
                    {
                        "name": name,
                        "baseline": baseline_time,
                        "llm": llm_time,
                        "diff_pct": diff_pct,
                        "diff_abs": diff_abs,
                        "methods": "Baseline vs LLM",
                    }
                )

        if ml_time and llm_time:
            diff_pct = abs((ml_time - llm_time) / llm_time) * 100
            diff_abs = abs(ml_time - llm_time)
            if diff_pct > 20 or diff_abs >= 4.0:
                large_discrepancies.append(
                    {
                        "name": name,
                        "ml": ml_time,
                        "llm": llm_time,
                        "diff_pct": diff_pct,
                        "diff_abs": diff_abs,
                        "methods": "ML vs LLM",
                    }
                )

        # Check for high variance (prediction spread > 15% of mean)
        times = [t for t in [baseline_time, ml_time, llm_time] if t is not None]
        if len(times) >= 2:
            mean_time = statistics.mean(times)
            max_time = max(times)
            min_time = min(times)
            spread = max_time - min_time
            spread_pct = (spread / mean_time) * 100

            if spread_pct > 15:
                high_variance_risk.append({"name": name, "min": min_time, "max": max_time, "spread_pct": spread_pct})

    # Calculate fairness metric (mark spread)
    [r["predicted_time"] for r in handicap_results]

    # Theoretical finish time spread (should be near zero for perfect handicaps)
    # finish_time = mark + predicted_time
    finish_times = [r["mark"] + r["predicted_time"] for r in handicap_results]
    finish_spread = max(finish_times) - min(finish_times)

    # Assess overall status
    critical_issues = []
    warnings = []
    info = []

    # Critical issues (recommend review)
    if len(large_discrepancies) > total_competitors * 0.3:  # >30% have large discrepancies
        critical_issues.append(
            f"{len(large_discrepancies)} competitors have prediction methods disagreeing >20% or >4s"
        )

    if len(low_confidence) > total_competitors * 0.4:  # >40% low confidence
        critical_issues.append(f"{len(low_confidence)} competitors have LOW confidence predictions")

    if finish_spread > 5.0:  # Finish spread >5 seconds
        critical_issues.append(f"Finish time spread is {finish_spread:.1f}s (should be <2s for fair handicaps)")

    # Warnings (review recommended but not critical)
    if len(scaled_predictions) > total_competitors * 0.5:  # >50% scaled
        warnings.append(f"{len(scaled_predictions)} competitors using cross-diameter scaling")

    if len(no_ml_predictions) == total_competitors:  # No ML at all
        warnings.append("ML predictions unavailable for all competitors (insufficient training data)")

    if len(large_discrepancies) > 0 and len(large_discrepancies) <= total_competitors * 0.3:
        warnings.append(f"{len(large_discrepancies)} competitors have prediction discrepancies >20% or >4s")

    # Info (normal operation notes)
    if finish_spread < 1.0:
        info.append(f"Excellent fairness: {finish_spread:.1f}s finish spread")
    elif finish_spread < 2.0:
        info.append(f"Good fairness: {finish_spread:.1f}s finish spread")

    primary_method = max(methods_used, key=methods_used.get)
    info.append(f"Primary prediction method: {primary_method} ({methods_used[primary_method]}/{total_competitors})")
    info.append("Selection uses lowest expected error (confidence, scaling penalties, CV MAE)")

    # Assumptions snapshot (judge awareness)
    assumptions = {
        "quality_scale": "1=softest, 10=hardest (higher = slower)",
        "variance_model": "Per-competitor std-dev with data-driven fallback",
        "heat_variance": "Shared heat variance included in Monte Carlo",
    }

    # Determine overall status
    if len(critical_issues) > 0:
        status = "REVIEW RECOMMENDED"
        recommendation = "Review competitors flagged below before approving handicaps."
    elif len(warnings) > 0:
        status = "CAUTION"
        recommendation = "Handicaps appear reasonable but note warnings below."
    else:
        status = "LOOKS GOOD"
        recommendation = "Handicaps validated - safe to approve."

    return {
        "status": status,
        "recommendation": recommendation,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "info": info,
        "details": {
            "total_competitors": total_competitors,
            "large_discrepancies": large_discrepancies,
            "low_confidence": low_confidence,
            "scaled_predictions": scaled_predictions,
            "no_ml_count": len(no_ml_predictions),
            "high_variance_risk": high_variance_risk,
            "finish_spread": finish_spread,
            "methods_used": methods_used,
            "assumptions": assumptions,
        },
    }


def display_check_my_work(handicap_results: List[Dict], wood_selection: Dict) -> None:
    """
    Display "Check My Work" validation summary to judge.

    Shows a concise, scannable summary of potential issues with handicaps.

    Args:
        handicap_results: List of competitor results with predictions
        wood_selection: Wood characteristics dict
    """
    print("\n" + "=" * 70)
    print("  CHECK MY WORK - Handicap Validation")
    print("=" * 70)

    # Run validation
    validation = check_my_work(handicap_results, wood_selection)

    if validation["status"] == "ERROR":
        print(f"\n[!] {validation['message']}")
        return

    # Display status with color-coded indicator
    status = validation["status"]
    if status == "LOOKS GOOD":
        status_icon = "[OK]"
    elif status == "CAUTION":
        status_icon = "[!]"
    else:  # REVIEW RECOMMENDED
        status_icon = "[!][!]"

    print(f"\n{status_icon} STATUS: {status}")
    print(f"\n{validation['recommendation']}")

    # Display critical issues
    if validation["critical_issues"]:
        print(f"\n{'-' * 70}")
        print("CRITICAL ISSUES:")
        for issue in validation["critical_issues"]:
            print(f"  [!] {issue}")

    # Display warnings
    if validation["warnings"]:
        print(f"\n{'-' * 70}")
        print("WARNINGS:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    # Display info
    if validation["info"]:
        print(f"\n{'-' * 70}")
        print("SUMMARY:")
        for info_item in validation["info"]:
            print(f"  [OK] {info_item}")

    # Show detailed breakdowns if issues exist
    details = validation["details"]

    if details["large_discrepancies"]:
        print(f"\n{'-' * 70}")
        print("PREDICTION DISCREPANCIES (>20% or >4s):")
        print(f"{'Competitor':<25} {'Methods':<20} {'Difference'}")
        print("-" * 70)
        for disc in details["large_discrepancies"][:10]:  # Limit to first 10
            if disc.get("diff_abs") is not None and disc["diff_abs"] >= 4.0:
                diff_str = f"{disc['diff_abs']:>4.1f}s"
            else:
                diff_str = f"{disc['diff_pct']:>6.1f}%"
            print(f"{disc['name']:<25} {disc['methods']:<20} {diff_str}")

        if len(details["large_discrepancies"]) > 10:
            print(f"\n...and {len(details['large_discrepancies']) - 10} more")

    if details["low_confidence"]:
        print(f"\n{'-' * 70}")
        print("LOW CONFIDENCE PREDICTIONS:")
        print(f"{'Competitor':<25} {'Confidence':<12} {'Reason'}")
        print("-" * 70)
        for low_conf in details["low_confidence"][:10]:  # Limit to first 10
            reason_short = low_conf["reason"][:30] + "..." if len(low_conf["reason"]) > 30 else low_conf["reason"]
            print(f"{low_conf['name']:<25} {low_conf['confidence']:<12} {reason_short}")

        if len(details["low_confidence"]) > 10:
            print(f"\n...and {len(details['low_confidence']) - 10} more")

    if details["scaled_predictions"]:
        print(f"\n{'-' * 70}")
        print("CROSS-DIAMETER SCALING:")
        print(f"{'Competitor':<25} {'Scaling Applied'}")
        print("-" * 70)
        for scaled in details["scaled_predictions"][:10]:  # Limit to first 10
            print(f"{scaled['name']:<25} {scaled['warning']}")

        if len(details["scaled_predictions"]) > 10:
            print(f"\n...and {len(details['scaled_predictions']) - 10} more (scaling applied)")

    # Show assumption snapshot
    if details.get("assumptions"):
        print(f"\n{'-' * 70}")
        print("ASSUMPTIONS SNAPSHOT:")
        print(f"  Quality scale: {details['assumptions']['quality_scale']}")
        print(f"  Variance model: {details['assumptions']['variance_model']}")
        print(f"  Heat effect: {details['assumptions']['heat_variance']}")

    # Final recommendation
    print(f"\n{'=' * 70}")

    if status == "LOOKS GOOD":
        print("[OK] VALIDATION PASSED - Handicaps appear fair and well-supported by data")
        print("  You can proceed with approval.")
    elif status == "CAUTION":
        print("[!] PROCEED WITH CAUTION - Some warnings detected")
        print("  Review warnings above, but handicaps should be acceptable.")
    else:  # REVIEW RECOMMENDED
        print("[!][!] REVIEW RECOMMENDED - Issues detected that may affect fairness")
        print("  Consider reviewing flagged competitors before approval.")
        print("  You may want to manually adjust specific handicaps (Option 5 -> 2).")

    print("=" * 70)
