"""
AI-Enhanced Time Prediction for Woodchopping Handicap System

This module provides LLM-based time predictions that combine historical data
with AI reasoning to adjust for wood quality and other contextual factors.

Functions:
    predict_competitor_time_with_ai() - Predict time using historical data + LLM quality adjustment
"""

import re
from typing import Dict, Optional, Tuple

import pandas as pd

# Import config
# Import local modules
from woodchopping.data import load_wood_data, standardize_results_data
from woodchopping.predictions.baseline import (
    apply_shrinkage,
    compute_robust_weighted_mean,
    get_competitor_historical_times_normalized,
    get_event_baseline_flexible,
    predict_baseline_v2_hybrid,
)
from woodchopping.predictions.llm import call_ollama


def predict_competitor_time_with_ai(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: pd.DataFrame,
    tournament_results: Optional[Dict[str, float]] = None,
) -> Tuple[float, str, str]:
    """
    Predict competitor's time using historical data + LLM reasoning for quality adjustment.

    This function implements a multi-stage prediction process:
    1. Get historical times (with cascading fallback)
    2. Calculate baseline time using weighted average
    3. Apply tournament result weighting if available (97% same-wood optimization)
    4. Use LLM to adjust baseline for wood quality
    5. Fallback to statistical adjustment if LLM unavailable

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality rating (1-10, where 5=average, >5=harder, <5=softer)
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame
        tournament_results: Optional dict of {competitor_name: actual_time} from same tournament
                          When provided, applies 97% weight to tournament time vs 3% historical

    Returns:
        Tuple of (predicted_time, confidence, explanation)
        - predicted_time: Float predicted time in seconds
        - confidence: "HIGH", "MEDIUM", "LOW", "VERY LOW", or "VERY HIGH" (with tournament data)
        - explanation: String describing prediction method and data source

    Example:
        >>> time, conf, exp = predict_competitor_time_with_ai(
        ...     "John Smith", "White Pine", 300, 7, "SB", results_df
        ... )
        >>> print(f"Predicted {time:.1f}s (confidence: {conf})")
        >>> print(f"Based on: {exp}")
    """
    # Normalize quality input (1-10 scale)
    quality = int(quality) if quality is not None else 5
    quality = max(1, min(10, quality))

    # Standardize results data (shared validation + outlier filtering)
    results_df, _ = standardize_results_data(results_df)

    # Step 1: Prefer Baseline V2 as the LLM anchor (quality=5 baseline), fallback to V1 if needed
    # Critical for aging competitors: recent performances weighted much higher than peak from years ago
    wood_df = load_wood_data()
    baseline = None
    confidence = "LOW"
    explanation_source = ""
    tournament_weighted = False

    try:
        baseline_v2, conf_v2, expl_v2, meta_v2 = predict_baseline_v2_hybrid(
            competitor_name=competitor_name,
            species=species,
            diameter=diameter,
            quality=5,  # LLM applies quality adjustment separately
            event_code=event_code,
            results_df=results_df,
            wood_df=wood_df,
            tournament_results=tournament_results,
            enable_calibration=False,
        )

        if baseline_v2 is not None:
            baseline = baseline_v2
            confidence = conf_v2
            explanation_source = f"Baseline V2: {expl_v2}"
            tournament_weighted = bool(meta_v2.get("tournament_weighted")) if meta_v2 else False
    except Exception:
        baseline = None

    historical_data = []
    data_source = ""
    if baseline is None:
        historical_data, data_source, _ = get_competitor_historical_times_normalized(
            competitor_name,
            species,
            diameter,
            event_code,
            results_df,
            return_weights=True,
            wood_df=wood_df,
        )

    # Step 2: Calculate time-weighted baseline (V1 fallback only)
    tournament_time = None

    if baseline is None:
        if len(historical_data) >= 3:
            # Use robust weighted mean (median/MAD clipping) to limit outlier impact
            baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
            event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df)
            if event_baseline is not None and baseline is not None:
                shrunk = apply_shrinkage(baseline, effective_n, event_baseline)
                if shrunk != baseline:
                    baseline = shrunk
                    explanation_source = (
                        f"robust time-weighted history {data_source} "
                        f"({len(historical_data)} results, avg weight {avg_weight:.2f}) "
                        f"+ shrinkage to {event_source}"
                    )
                else:
                    explanation_source = (
                        f"robust time-weighted history {data_source} "
                        f"({len(historical_data)} results, avg weight {avg_weight:.2f})"
                    )
            else:
                explanation_source = (
                    f"robust time-weighted history {data_source} "
                    f"({len(historical_data)} results, avg weight {avg_weight:.2f})"
                )
            confidence = "HIGH"

        elif len(historical_data) > 0:
            # Limited history - still apply robust weighting
            baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
            event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df)
            if event_baseline is not None and baseline is not None:
                shrunk = apply_shrinkage(baseline, effective_n, event_baseline)
                if shrunk != baseline:
                    baseline = shrunk
                    explanation_source = (
                        f"limited robust history {data_source} "
                        f"({len(historical_data)} results, avg weight {avg_weight:.2f}) "
                        f"+ shrinkage to {event_source}"
                    )
                else:
                    explanation_source = (
                        f"limited robust history {data_source} "
                        f"({len(historical_data)} results, avg weight {avg_weight:.2f})"
                    )
            else:
                explanation_source = (
                    f"limited robust history {data_source} "
                    f"({len(historical_data)} results, avg weight {avg_weight:.2f})"
                )
            confidence = "MEDIUM"

        else:
            baseline, baseline_source = get_event_baseline_flexible(
                species, diameter, event_code, results_df, wood_df=wood_df
            )

            if baseline:
                confidence = "LOW"
                explanation_source = f"{baseline_source} (no competitor history)"
            else:
                if diameter >= 350:
                    baseline = 60.0
                elif diameter >= 300:
                    baseline = 50.0
                elif diameter >= 275:
                    baseline = 45.0
                else:
                    baseline = 40.0

                confidence = "VERY LOW"
                explanation_source = "estimated from size (no historical data)"

    # Step 2.5: Apply tournament result weighting (97% same-wood optimization)
    # CRITICAL V4.4 FEATURE: Tournament results from same wood beat historical data
    historical_baseline_for_context = baseline  # Save for prompt context
    if (not tournament_weighted) and tournament_results and competitor_name in tournament_results:
        tournament_time = tournament_results[competitor_name]
        tournament_weighted = True

        # Apply 97% tournament, 3% historical weighting
        baseline = (tournament_time * 0.97) + (baseline * 0.03)
        confidence = "VERY HIGH"
        explanation_source = f"Tournament result ({tournament_time:.1f}s @ 97%) + {explanation_source} (@ 3%)"

    # Format wood species data for AI
    wood_data_text = ""
    if wood_df is not None and not wood_df.empty:
        wood_data_text = "\nAVAILABLE WOOD SPECIES DATABASE:\n"
        for _, row in wood_df.iterrows():
            species_name = row.get("species", "Unknown")
            wood_data_text += f"  - {species_name}"
            if "hardness_category" in row:
                wood_data_text += f": Category={row.get('hardness_category', 'N/A')}"
            if "base_adjustment_pct" in row:
                wood_data_text += f", Base Adjustment={row.get('base_adjustment_pct', 0):+.1f}%"
            if "description" in row:
                wood_data_text += f", Description: {row.get('description', '')}"
            wood_data_text += "\n"

    # Step 3: AI calibration prompt (returns multiplier)
    # Build tournament context section if applicable
    tournament_context_section = ""
    if tournament_weighted and tournament_time:
        tournament_context_section = f"""
[WARN]? TOURNAMENT CONTEXT - CRITICAL INFORMATION [WARN]?

This competitor has ALREADY COMPETED in this tournament on THIS EXACT WOOD.
Tournament result: {tournament_time:.1f} seconds (recorded in heat/semi, same block)

IMPORTANCE OF SAME-WOOD DATA:
- Same wood across rounds = MOST ACCURATE predictor possible
- Tournament result from TODAY beats historical data from YEARS AGO
- System applies 97% weight to tournament time, 3% to historical baseline
- Your quality adjustment should be MINIMAL - wood characteristics already proven

BASELINE CALCULATION FOR THIS CASE:
Baseline {baseline:.1f}s = (Tournament {tournament_time:.1f}s x 97%) + (Historical {historical_baseline_for_context:.1f}s x 3%)

YOUR TASK: Apply MINOR quality adjustment ONLY if wood quality has changed since tournament round.
Expected adjustment range: ±1-3% maximum (wood is proven via tournament result)
Do NOT apply standard quality adjustments - this is PROVEN data from SAME WOOD.
"""

    prompt = f"""You are a master woodchopping handicapper making precision time predictions for competition.

HANDICAPPING OBJECTIVE

Your prediction must account for wood characteristics and competitor ability to create fair handicaps.
When handicaps are applied, all competitors should finish simultaneously if your predictions are accurate.
This requires deep understanding of how wood properties affect cutting times.

COMPETITOR PROFILE

Name: {competitor_name}
Baseline Time: {baseline:.1f} seconds
Data Source: {explanation_source}
Confidence Level: {confidence}
{tournament_context_section}
BASELINE INTERPRETATION:
- {"This baseline is HEAVILY WEIGHTED (97%) toward same-tournament result - wood is PROVEN" if tournament_weighted else "This baseline assumes QUALITY 5 wood (average hardness)"}
- Your task is to adjust this baseline for the ACTUAL quality rating
- {"Apply MINIMAL adjustment - tournament result already reflects wood characteristics" if tournament_weighted else "Historical data already accounts for competitor's skill level and typical conditions"}

WOOD SPECIFICATIONS

Species: {species}
Diameter: {diameter:.0f}mm
Quality Rating: {quality}/10
Event Type: {event_code}

WOOD CHARACTERISTICS DATABASE
{wood_data_text}

QUALITY RATING SYSTEM - CRITICAL UNDERSTANDING

Quality measures wood HARDNESS on a 1-10 scale:
- HIGHER number = HARDER wood = SLOWER cutting = HIGHER time
- LOWER number = SOFTER wood = FASTER cutting = LOWER time

10 = Extremely hard/barely suitable
   - Maximum difficulty
   - SLOWEST possible cutting time
   - MULTIPLY baseline by 1.12-1.15 (increase by 12-15%)
   - Example: 40s baseline -> 45-46s predicted

9 = Very hard
   - Major difficulty, knots, irregular grain
   - MULTIPLY baseline by 1.08-1.12 (increase by 8-12%)
   - Example: 40s baseline -> 43-45s predicted

8 = Hard
   - Significant resistance, green wood, tough grain
   - MULTIPLY baseline by 1.05-1.08 (increase by 5-8%)
   - Example: 40s baseline -> 42-43s predicted

7 = Moderately hard
   - Noticeably tougher, more resistance
   - MULTIPLY baseline by 1.03-1.05 (increase by 3-5%)
   - Example: 40s baseline -> 41-42s predicted

6 = Slightly hard
   - Marginally tougher than average
   - MULTIPLY baseline by 1.01-1.03 (increase by 1-3%)
   - Example: 40s baseline -> 40-41s predicted

5 = AVERAGE HARDNESS (BASELINE REFERENCE POINT)
   - This is what the baseline time assumes
   - MULTIPLY baseline by 1.00 (NO ADJUSTMENT)
   - Example: 40s baseline -> 40s predicted

4 = Slightly soft
   - Marginally easier than average
   - MULTIPLY baseline by 0.97-0.99 (reduce by 1-3%)
   - Example: 40s baseline -> 39-40s predicted

3 = Moderately soft
   - Better cutting conditions
   - MULTIPLY baseline by 0.95-0.97 (reduce by 3-5%)
   - Example: 40s baseline -> 38-39s predicted

2 = Soft
   - Good cutting conditions, easy to work with
   - MULTIPLY baseline by 0.93-0.95 (reduce by 5-7%)
   - Example: 40s baseline -> 37-38s predicted

1 = Very soft/rotten
   - Wood breaks apart easily, minimal resistance
   - FASTEST possible cutting time
   - MULTIPLY baseline by 0.85-0.90 (reduce by 10-15%)
   - Example: 40s baseline -> 34-36s predicted

CURRENT SITUATION ANALYSIS

Baseline time: {baseline:.1f}s (assumes quality 5 wood)
Your wood quality: {quality}/10

Quality deviation: {quality - 5:+d} points from baseline reference

CRITICAL CALCULATION DIRECTION:
{"[WARN]? Quality " + str(quality) + " > 5 means HARDER wood -> SLOWER cutting -> HIGHER time than baseline" if quality > 5 else "[WARN]? Quality " + str(quality) + " < 5 means SOFTER wood -> FASTER cutting -> LOWER time than baseline" if quality < 5 else "[OK] Quality 5 = baseline assumption -> NO ADJUSTMENT needed"}

{"Expected multiplier: 1.01-1.03 (increase baseline by 1-3%)" if quality == 6 else "Expected multiplier: 1.03-1.05 (increase baseline by 3-5%)" if quality == 7 else "Expected multiplier: 1.05-1.08 (increase baseline by 5-8%)" if quality == 8 else "Expected multiplier: 1.08-1.12 (increase baseline by 8-12%)" if quality >= 9 else "Expected multiplier: 0.97-0.99 (reduce baseline by 1-3%)" if quality == 4 else "Expected multiplier: 0.95-0.97 (reduce baseline by 3-5%)" if quality == 3 else "Expected multiplier: 0.93-0.95 (reduce baseline by 5-7%)" if quality == 2 else "Expected multiplier: 0.85-0.90 (reduce baseline by 10-15%)" if quality == 1 else "Expected multiplier: 1.00 (no change)"}

{"Target range: " + str(round(baseline * 1.01, 1)) + "s - " + str(round(baseline * 1.03, 1)) + "s" if quality == 6 else "Target range: " + str(round(baseline * 1.03, 1)) + "s - " + str(round(baseline * 1.05, 1)) + "s" if quality == 7 else "Target range: " + str(round(baseline * 1.05, 1)) + "s - " + str(round(baseline * 1.08, 1)) + "s" if quality == 8 else "Target range: " + str(round(baseline * 1.08, 1)) + "s - " + str(round(baseline * 1.12, 1)) + "s" if quality >= 9 else "Target range: " + str(round(baseline * 0.97, 1)) + "s - " + str(round(baseline * 0.99, 1)) + "s" if quality == 4 else "Target range: " + str(round(baseline * 0.95, 1)) + "s - " + str(round(baseline * 0.97, 1)) + "s" if quality == 3 else "Target range: " + str(round(baseline * 0.93, 1)) + "s - " + str(round(baseline * 0.95, 1)) + "s" if quality == 2 else "Target range: " + str(round(baseline * 0.85, 1)) + "s - " + str(round(baseline * 0.90, 1)) + "s" if quality == 1 else "Target: " + str(round(baseline, 1)) + "s (baseline)"}

CALCULATION METHODOLOGY

Step 1: Start with baseline time: {baseline:.1f}s

Step 2: Apply species base adjustment (if available in database)
- Check species database above for {species}
- Apply the base adjustment percentage if listed

Step 3: Apply quality adjustment
- Calculate deviation from quality 5: {quality} - 5 = {quality - 5}
- Apply adjustment based on quality scale above
- Use the percentage ranges provided (1.5-2.5% per point as guideline)

Step 4: Consider wood physics
- Softer wood (quality <5): Cuts faster, less resistance
- Harder wood (quality >5): Cuts slower, more resistance
- Effect is roughly linear in the middle range (3-7)
- Effect accelerates at extremes (0-2 and 8-10)

Step 5: Validate against typical ranges for {diameter:.0f}mm diameter
- 275mm diameter: 35-50s typical range
- 300mm diameter: 40-55s typical range
- 325mm diameter: 45-60s typical range
- 350mm diameter: 50-70s typical range
- 375mm+ diameter: 60-90s typical range

CRITICAL FACTORS FOR FAIR HANDICAPPING

Front/Back Marker Dynamics:
- Softer wood (quality <5) disproportionately benefits slower competitors (front markers)
  * They gain more time than expected from easier cutting
  * Risk: Front marker finishes before back marker even starts

- Harder wood (quality >5) disproportionately penalizes slower competitors
  * They lose more time than expected from difficult cutting
  * Risk: Back marker wins by excessive margin

Your adjustment must account for this to maintain fair handicapping.

WOOD DENSITY AND SIZE INTERACTION

The {diameter:.0f}mm diameter creates a cutting area of approximately {3.14159 * (diameter / 2) ** 2 / 10000:.2f} square cm.
- Larger diameter = exponentially more wood volume to remove
- Quality affects this proportionally: softer wood on large diameter saves significant time
- This diameter/quality interaction is already partially in baseline, but verify your adjustment makes sense

RESPONSE REQUIREMENT

Return your analysis in this EXACT format (3 parts separated by " | "):

<multiplier> | <confidence> | <explanation>

Where:
- <multiplier> = decimal between 0.85 and 1.15 (e.g., 1.07)
- <confidence> = HIGH, MEDIUM, or LOW based on:
  * HIGH: Quality clearly defined, well within typical range
  * MEDIUM: Borderline quality or limited data
  * LOW: Extreme quality or unusual conditions
- <explanation> = ONE sentence explaining quality adjustment reasoning (max 15 words)

Examples:
1.07 | HIGH | Quality 8 wood increases cutting resistance by approximately 7%
0.95 | HIGH | Quality 3 wood reduces cutting time by approximately 5%
1.00 | MEDIUM | Quality 5 is average, no adjustment needed
1.12 | MEDIUM | Quality 10 is extremely hard, borderline acceptable wood

Your response:"""

    response = call_ollama(prompt)

    if response is None:
        # Fallback: statistical quality adjustment
        quality_adjustment = (quality - 5) * 0.02
        predicted_time = baseline * (1 + quality_adjustment)
        explanation = f"Predicted {predicted_time:.1f}s ({explanation_source}, quality adjusted)"
        return predicted_time, confidence, explanation

    try:
        # Parse LLM response - expecting format: "multiplier | confidence | explanation"
        response = response.strip()

        # Try to split by pipe delimiter
        if "|" in response:
            parts = [p.strip() for p in response.split("|")]
            if len(parts) >= 3:
                # Extract all three components
                multiplier_str = parts[0]
                llm_confidence = parts[1].upper()
                quality_explanation = parts[2]

                # Parse multiplier
                numbers = re.findall(r"\d+\.?\d*", multiplier_str)
                if numbers:
                    multiplier = float(numbers[0])

                    # Sanity check: multiplier should be within strict bounds
                    if 0.85 <= multiplier <= 1.15:
                        predicted_time = baseline * multiplier
                        # Sanity check: prediction should be within 50% of baseline
                        if baseline * 0.5 <= predicted_time <= baseline * 1.5:
                            # Combine historical confidence with LLM confidence
                            # If LLM says LOW confidence, downgrade overall confidence
                            if llm_confidence == "LOW" and confidence == "HIGH":
                                confidence = "MEDIUM"
                            elif llm_confidence == "LOW" and confidence == "MEDIUM":
                                confidence = "LOW"

                            # Build rich explanation incorporating LLM reasoning
                            explanation = f"Predicted {predicted_time:.1f}s ({explanation_source}, AI calibrated: {quality_explanation})"
                            return predicted_time, confidence, explanation

        # If structured parsing fails, try fallback to old format (single number)
        numbers = re.findall(r"\d+\.?\d*", response)
        if numbers:
            multiplier = float(numbers[0])

            # Sanity check: multiplier should be within strict bounds
            if 0.85 <= multiplier <= 1.15:
                predicted_time = baseline * multiplier
                # Sanity check: prediction should be within 50% of baseline
                if baseline * 0.5 <= predicted_time <= baseline * 1.5:
                    explanation = f"Predicted {predicted_time:.1f}s ({explanation_source}, AI calibrated)"
                    return predicted_time, confidence, explanation
    except Exception:
        # Log parsing failure silently, fall through to baseline
        pass

    # If LLM parsing fails, return baseline
    explanation = f"Predicted {baseline:.1f}s ({explanation_source})"
    return baseline, confidence, explanation
