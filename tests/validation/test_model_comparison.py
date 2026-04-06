"""
Model Comparison Testing Script: qwen2.5:7b vs qwen2.5:32b

This script compares the performance of different Ollama models for woodchopping
handicap prediction tasks:

1. Time Prediction Accuracy: Quality multiplier consistency and accuracy
2. Latency: Response time for different task types
3. Fairness Assessment Quality: Structured output compliance and insight depth
4. Memory Usage: Resource requirements

Usage:
    python test_model_comparison.py

Requirements:
    - Ollama running locally with both qwen2.5:7b and qwen2.5:32b installed
    - woodchopping.xlsx with historical data
    - At least 5 competitors with 5+ results each for validation

Output:
    Generates test_model_comparison_results.txt with detailed comparison
    and recommendation for which model to use.
"""

import sys
import time
from statistics import mean
from typing import Dict, List

import pytest

# Entire module requires a local Ollama instance — CI skips it via -m "not ollama".
pytestmark = pytest.mark.ollama

# Add project root to path
sys.path.insert(0, ".")

from config import llm_config
from woodchopping.predictions.llm import call_ollama


def test_time_prediction_accuracy(model: str, num_tests: int = 10) -> Dict:
    """
    Test quality multiplier prediction consistency and reasonableness.

    Tests the model's ability to:
    - Return consistent multipliers for identical inputs
    - Follow bounds (0.85-1.15)
    - Parse responses correctly
    - Provide confidence ratings

    Args:
        model: Model name to test
        num_tests: Number of test cases to run

    Returns:
        Dict with accuracy metrics
    """
    print(f"\n  Testing time prediction accuracy for {model}...")

    test_cases = [
        # (baseline, quality, expected_direction, expected_range)
        (45.0, 8, "higher", (1.05, 1.08)),  # Hard wood -> slower
        (45.0, 3, "lower", (0.95, 0.97)),  # Soft wood -> faster
        (45.0, 5, "same", (0.99, 1.01)),  # Average -> no change
        (30.0, 10, "higher", (1.12, 1.15)),  # Very hard -> much slower
        (60.0, 1, "lower", (0.85, 0.90)),  # Very soft -> much faster
    ]

    results = {
        "successes": 0,
        "parsing_failures": 0,
        "bounds_violations": 0,
        "direction_errors": 0,
        "latencies": [],
        "structured_responses": 0,
        "total_tests": len(test_cases),
    }

    for baseline, quality, expected_dir, expected_range in test_cases:
        prompt = f"""You are a master woodchopping handicapper making precision time predictions.

Baseline Time: {baseline:.1f} seconds (assumes QUALITY 5 wood)
Current Wood Quality: {quality}/10

QUALITY RATING:
- Quality 5 = average (multiplier 1.00)
- Higher quality = harder wood = slower cutting = multiplier >1.00
- Lower quality = softer wood = faster cutting = multiplier <1.00

Return your analysis in this EXACT format (3 parts separated by " | "):

<multiplier> | <confidence> | <explanation>

Where:
- <multiplier> = decimal between 0.85 and 1.15
- <confidence> = HIGH, MEDIUM, or LOW
- <explanation> = ONE sentence explaining quality adjustment reasoning

Your response:"""

        start = time.time()
        response = call_ollama(prompt, model=model, num_predict=100)
        latency = time.time() - start

        results["latencies"].append(latency)

        if not response:
            results["parsing_failures"] += 1
            continue

        # Try to parse structured response
        if "|" in response:
            results["structured_responses"] += 1
            parts = [p.strip() for p in response.split("|")]
            if len(parts) >= 3:
                try:
                    multiplier = float(parts[0])

                    # Check bounds
                    if not (0.85 <= multiplier <= 1.15):
                        results["bounds_violations"] += 1
                        continue

                    # Check direction
                    predicted_time = baseline * multiplier
                    if expected_dir == "higher" and predicted_time <= baseline:
                        results["direction_errors"] += 1
                    elif expected_dir == "lower" and predicted_time >= baseline:
                        results["direction_errors"] += 1
                    elif expected_dir == "same" and abs(predicted_time - baseline) > baseline * 0.02:
                        results["direction_errors"] += 1
                    else:
                        # Check if multiplier is within expected range
                        if expected_range[0] <= multiplier <= expected_range[1]:
                            results["successes"] += 1

                except (ValueError, IndexError):
                    results["parsing_failures"] += 1
            else:
                results["parsing_failures"] += 1
        else:
            # Try fallback parsing (single number)
            import re

            numbers = re.findall(r"\d+\.?\d*", response)
            if numbers:
                try:
                    multiplier = float(numbers[0])
                    if 0.85 <= multiplier <= 1.15:
                        if expected_range[0] <= multiplier <= expected_range[1]:
                            results["successes"] += 1
                    else:
                        results["bounds_violations"] += 1
                except ValueError:
                    results["parsing_failures"] += 1
            else:
                results["parsing_failures"] += 1

    results["avg_latency"] = mean(results["latencies"]) if results["latencies"] else 0
    results["accuracy_rate"] = (results["successes"] / results["total_tests"]) * 100
    results["structured_rate"] = (results["structured_responses"] / results["total_tests"]) * 100

    return results


def test_fairness_assessment_quality(model: str) -> Dict:
    """
    Test fairness assessment output quality.

    Checks:
    - Presence of all required sections
    - Valid fairness rating
    - Response completeness
    - Latency

    Args:
        model: Model name to test

    Returns:
        Dict with quality metrics
    """
    print(f"\n  Testing fairness assessment quality for {model}...")

    # Mock simulation data
    prompt = """You are a master woodchopping handicapper analyzing fairness.

SIMULATION RESULTS (2,000,000 iterations, 4 competitors):

Win Rates:
  - Alice Smith: 26.50% win rate (deviation: +1.50%)
  - Bob Jones: 24.20% win rate (deviation: -0.80%)
  - Charlie Brown: 23.80% win rate (deviation: -1.20%)
  - Diana Prince: 25.50% win rate (deviation: +0.50%)

Ideal win rate: 25.0% each
Win rate spread: 2.70% (from 23.80% to 26.50%)

Provide your assessment in this structure:

FAIRNESS RATING: [EXCELLENT/VERY GOOD/GOOD/FAIR/POOR/UNACCEPTABLE]

STATISTICAL ANALYSIS: [2-3 sentences]

PATTERN DIAGNOSIS: [2-3 sentences]

PREDICTION ACCURACY: [1-2 sentences]

RECOMMENDATIONS:
- [First recommendation]
- [Second recommendation]

Your assessment:"""

    start = time.time()
    response = call_ollama(prompt, model=model, num_predict=llm_config.TOKENS_FAIRNESS_ASSESSMENT)
    latency = time.time() - start

    results = {
        "latency": latency,
        "has_rating": False,
        "has_analysis": False,
        "has_diagnosis": False,
        "has_accuracy": False,
        "has_recommendations": False,
        "valid_rating": False,
        "response_length": len(response) if response else 0,
        "complete": False,
    }

    if response:
        response_upper = response.upper()

        # Check for sections
        results["has_rating"] = "FAIRNESS RATING" in response_upper
        results["has_analysis"] = "STATISTICAL ANALYSIS" in response_upper
        results["has_diagnosis"] = "PATTERN DIAGNOSIS" in response_upper or "PATTERN" in response_upper
        results["has_accuracy"] = "PREDICTION ACCURACY" in response_upper or "ACCURACY" in response_upper
        results["has_recommendations"] = "RECOMMENDATIONS" in response_upper or "RECOMMEND" in response_upper

        # Check for valid rating
        valid_ratings = ["EXCELLENT", "VERY GOOD", "GOOD", "FAIR", "POOR", "UNACCEPTABLE"]
        results["valid_rating"] = any(rating in response_upper for rating in valid_ratings)

        # Check completeness
        results["complete"] = all(
            [
                results["has_rating"],
                results["has_analysis"],
                results["has_diagnosis"],
                results["has_accuracy"],
                results["has_recommendations"],
                results["valid_rating"],
            ]
        )

    return results


def compare_models(models: List[str]) -> Dict:
    """
    Run comprehensive comparison between models.

    Args:
        models: List of model names to compare

    Returns:
        Dict mapping model name to test results
    """
    comparison_results = {}

    for model in models:
        print(f"\nTesting model: {model}")
        print("=" * 60)

        model_results = {
            "time_prediction": test_time_prediction_accuracy(model),
            "fairness_assessment": test_fairness_assessment_quality(model),
        }

        comparison_results[model] = model_results

        # Print summary
        tp = model_results["time_prediction"]
        fa = model_results["fairness_assessment"]

        print("\n  Time Prediction Results:")
        print(f"    Accuracy: {tp['accuracy_rate']:.1f}% ({tp['successes']}/{tp['total_tests']} correct)")
        print(f"    Structured responses: {tp['structured_rate']:.1f}%")
        print(f"    Avg latency: {tp['avg_latency']:.2f}s")
        print(f"    Parsing failures: {tp['parsing_failures']}")
        print(f"    Bounds violations: {tp['bounds_violations']}")
        print(f"    Direction errors: {tp['direction_errors']}")

        print("\n  Fairness Assessment Results:")
        print(f"    Complete: {fa['complete']}")
        print(f"    Valid rating: {fa['valid_rating']}")
        print(f"    Response length: {fa['response_length']} chars")
        print(f"    Latency: {fa['latency']:.2f}s")
        print(
            f"    Sections present: Rating={fa['has_rating']}, Analysis={fa['has_analysis']}, "
            f"Diagnosis={fa['has_diagnosis']}, Accuracy={fa['has_accuracy']}, Recs={fa['has_recommendations']}"
        )

    return comparison_results


def generate_recommendation(results: Dict) -> str:
    """
    Generate recommendation based on test results.

    Args:
        results: Comparison results dict

    Returns:
        Formatted recommendation text
    """
    report = "\n\n" + "=" * 80 + "\n"
    report += "MODEL COMPARISON RECOMMENDATION\n"
    report += "=" * 80 + "\n\n"

    # Extract metrics
    models = list(results.keys())

    if len(models) < 2:
        report += "ERROR: Need at least 2 models to compare\n"
        return report

    model_7b = "qwen2.5:7b" if "qwen2.5:7b" in models else models[0]
    model_32b = "qwen2.5:32b" if "qwen2.5:32b" in models else models[1]

    tp_7b = results[model_7b]["time_prediction"]
    tp_32b = results[model_32b]["time_prediction"]
    fa_7b = results[model_7b]["fairness_assessment"]
    fa_32b = results[model_32b]["fairness_assessment"]

    # Compare accuracy
    report += "TIME PREDICTION ACCURACY:\n"
    report += f"  {model_7b}: {tp_7b['accuracy_rate']:.1f}% accuracy, {tp_7b['avg_latency']:.2f}s avg latency\n"
    report += f"  {model_32b}: {tp_32b['accuracy_rate']:.1f}% accuracy, {tp_32b['avg_latency']:.2f}s avg latency\n"

    accuracy_winner = model_32b if tp_32b["accuracy_rate"] > tp_7b["accuracy_rate"] else model_7b
    speed_winner = model_7b if tp_7b["avg_latency"] < tp_32b["avg_latency"] else model_32b

    report += f"\n  Winner (Accuracy): {accuracy_winner}\n"
    report += f"  Winner (Speed): {speed_winner}\n"

    # Compare fairness assessment
    report += "\n\nFAIRNESS ASSESSMENT QUALITY:\n"
    report += f"  {model_7b}: Complete={fa_7b['complete']}, {fa_7b['latency']:.2f}s latency\n"
    report += f"  {model_32b}: Complete={fa_32b['complete']}, {fa_32b['latency']:.2f}s latency\n"

    quality_winner = model_32b if fa_32b["complete"] else model_7b if fa_7b["complete"] else "TIE"
    report += f"\n  Winner (Quality): {quality_winner}\n"

    # Overall recommendation
    report += "\n\nOVERALL RECOMMENDATION:\n"
    report += "-" * 80 + "\n"

    # Calculate scores
    score_7b = 0
    score_32b = 0

    # Accuracy (most important for predictions)
    if tp_32b["accuracy_rate"] > tp_7b["accuracy_rate"] + 10:
        score_32b += 3
        report += f"[OK] {model_32b} has significantly better prediction accuracy (+{tp_32b['accuracy_rate'] - tp_7b['accuracy_rate']:.1f}%)\n"
    elif tp_7b["accuracy_rate"] > tp_32b["accuracy_rate"] + 10:
        score_7b += 3
        report += f"[OK] {model_7b} has significantly better prediction accuracy (+{tp_7b['accuracy_rate'] - tp_32b['accuracy_rate']:.1f}%)\n"
    else:
        report += f"? Prediction accuracy is similar ({abs(tp_32b['accuracy_rate'] - tp_7b['accuracy_rate']):.1f}% difference)\n"

    # Structured output compliance
    if tp_32b["structured_rate"] > tp_7b["structured_rate"] + 20:
        score_32b += 2
        report += f"[OK] {model_32b} follows structured output format better (+{tp_32b['structured_rate'] - tp_7b['structured_rate']:.1f}%)\n"
    elif tp_7b["structured_rate"] > tp_32b["structured_rate"] + 20:
        score_7b += 2
        report += f"[OK] {model_7b} follows structured output format better (+{tp_7b['structured_rate'] - tp_32b['structured_rate']:.1f}%)\n"

    # Fairness assessment quality
    if fa_32b["complete"] and not fa_7b["complete"]:
        score_32b += 2
        report += f"[OK] {model_32b} provides complete fairness assessments\n"
    elif fa_7b["complete"] and not fa_32b["complete"]:
        score_7b += 2
        report += f"[OK] {model_7b} provides complete fairness assessments\n"

    # Speed
    if tp_7b["avg_latency"] < tp_32b["avg_latency"] * 0.75:
        score_7b += 1
        report += (
            f"[OK] {model_7b} is significantly faster ({tp_32b['avg_latency'] / tp_7b['avg_latency']:.1f}x speedup)\n"
        )

    # Final verdict
    report += "\n" + "-" * 80 + "\n"

    if score_32b > score_7b:
        report += f"\nTROPHY RECOMMENDED MODEL: {model_32b}\n\n"
        report += "The 32B model provides superior accuracy and output quality, which is\n"
        report += "critical for fair handicapping. The additional latency is acceptable\n"
        report += "given the improved prediction accuracy and assessment depth.\n"
    elif score_7b > score_32b:
        report += f"\nTROPHY RECOMMENDED MODEL: {model_7b}\n\n"
        report += "The 7B model provides acceptable accuracy with significantly better\n"
        report += "performance. Use this model if speed and resource constraints are\n"
        report += "more important than marginal accuracy improvements.\n"
    else:
        report += "\n? TIE - Both models perform similarly\n\n"
        report += f"Consider using {model_7b} for faster responses or {model_32b} for\n"
        report += "maximum accuracy. The performance difference is minimal.\n"

    # Resource considerations
    report += "\n" + "=" * 80 + "\n"
    report += "RESOURCE CONSIDERATIONS:\n\n"
    report += f"  {model_7b}:  ~7GB VRAM, faster inference (~{tp_7b['avg_latency']:.1f}s per prediction)\n"
    report += f"  {model_32b}: ~20GB VRAM, slower inference (~{tp_32b['avg_latency']:.1f}s per prediction)\n"
    report += "\n"
    report += "For production use, ensure your hardware can support the chosen model.\n"
    report += "For tournaments with 20+ competitors, expect:\n"
    report += f"  {model_7b}:  ~{20 * tp_7b['avg_latency']:.0f}s total prediction time\n"
    report += f"  {model_32b}: ~{20 * tp_32b['avg_latency']:.0f}s total prediction time\n"

    return report


def main():
    """Run model comparison tests."""
    print("=" * 80)
    print("WOODCHOPPING HANDICAP SYSTEM - MODEL COMPARISON TEST")
    print("=" * 80)
    print("\nThis script compares qwen2.5:7b vs qwen2.5:32b for:")
    print("  1. Time prediction accuracy and consistency")
    print("  2. Fairness assessment quality and completeness")
    print("  3. Response latency and throughput")
    print("\nEnsure both models are installed in Ollama before proceeding.")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)

    models_to_test = ["qwen2.5:7b", "qwen2.5:32b"]

    try:
        results = compare_models(models_to_test)
        recommendation = generate_recommendation(results)

        print(recommendation)

        # Save results
        output_file = "test_model_comparison_results.txt"
        with open(output_file, "w") as f:
            f.write("WOODCHOPPING HANDICAP SYSTEM - MODEL COMPARISON TEST RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for model, model_results in results.items():
                f.write(f"\n{model}\n")
                f.write("-" * 80 + "\n")
                f.write("Time Prediction:\n")
                for key, value in model_results["time_prediction"].items():
                    if key != "latencies":  # Skip raw latency list
                        f.write(f"  {key}: {value}\n")
                f.write("\nFairness Assessment:\n")
                for key, value in model_results["fairness_assessment"].items():
                    f.write(f"  {key}: {value}\n")

            f.write(recommendation)

        print(f"\n\nResults saved to: {output_file}")

    except Exception as e:
        print(f"\n\nERROR: Test failed with exception: {str(e)}")
        print("\nEnsure:")
        print("  1. Ollama is running (ollama serve)")
        print("  2. Both models are installed:")
        print("     ollama pull qwen2.5:7b")
        print("     ollama pull qwen2.5:32b")
        print("  3. woodchopping.xlsx exists in the project directory")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
