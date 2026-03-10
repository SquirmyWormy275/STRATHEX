"""
Prediction Aggregator for Woodchopping Handicap System

This module aggregates predictions from multiple methods (Baseline, ML, LLM)
and provides comparison, analysis, and selection of the best prediction.

Functions:
    get_all_predictions() - Get predictions from all three methods
    select_best_prediction() - Select best prediction with priority logic
    generate_prediction_analysis_llm() - LLM analysis of prediction differences
    display_dual_predictions() - Display all predictions side-by-side
"""

import statistics
import textwrap
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Import local modules
from woodchopping.data import load_results_df, standardize_results_data
from woodchopping.predictions.baseline import (
    get_competitor_historical_times_normalized,
    get_event_baseline_flexible,
    compute_robust_weighted_mean,
    apply_shrinkage,
    predict_baseline_v2_hybrid,
    fit_and_cache_baseline_v2_model,
)
from woodchopping.predictions.ml_model import (
    predict_time_ml,
    _model_training_data_size,
    get_model_cv_metrics,
)
from woodchopping.predictions.ai_predictor import predict_competitor_time_with_ai
from woodchopping.predictions.llm import call_ollama
from woodchopping.predictions.diameter_scaling import (
    get_diameter_info_from_historical_data,
    adjust_confidence_for_scaling
)


def get_all_predictions(
    competitor_name: str,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    tournament_results: Optional[Dict[str, float]] = None
) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Get predictions from all three methods: Baseline, ML, and LLM.

    CRITICAL ENHANCEMENT: When tournament_results is provided (semis/finals), same-tournament
    times are weighted at 97% vs historical data (3%). This provides maximum accuracy since
    the wood is identical across all rounds.

    Args:
        competitor_name: Competitor's name
        species: Wood species code
        diameter: Diameter in mm
        quality: Wood quality (1-10)
        event_code: Event type (SB or UH)
        results_df: Historical results DataFrame (optional)
        tournament_results: Optional dict of {competitor_name: actual_time} from THIS tournament

    Returns:
        dict with keys 'baseline', 'ml', 'llm', each containing:
            {
                'time': float or None,
                'confidence': str or None,
                'explanation': str or None,
                'error': str or None,
                'tournament_weighted': bool (True if tournament result used)
            }

    Example:
        >>> preds = get_all_predictions("John Smith", "WP", 300, 5, "SB")
        >>> if preds['ml']['time']:
        ...     print(f"ML: {preds['ml']['time']:.1f}s")
        >>> if preds['llm']['time']:
        ...     print(f"LLM: {preds['llm']['time']:.1f}s")
    """
    predictions = {
        'baseline': {
            'time': None, 'confidence': None, 'explanation': None, 'error': None,
            'scaled': False, 'original_diameter': None, 'scaling_warning': None,
            'tournament_weighted': False, 'std_dev': None, 'metadata': None
        },
        'ml': {
            'time': None, 'confidence': None, 'explanation': None, 'error': None,
            'scaled': False, 'original_diameter': None, 'scaling_warning': None,
            'tournament_weighted': False
        },
        'llm': {
            'time': None, 'confidence': None, 'explanation': None, 'error': None,
            'scaled': False, 'original_diameter': None, 'scaling_warning': None,
            'tournament_weighted': False
        }
    }

    # Load results once
    if results_df is None:
        results_df = load_results_df()

    # Standardize results data (shared validation + outlier filtering)
    results_df, _ = standardize_results_data(results_df)

    # Get historical diameter info (used for ML/LLM warnings)
    hist_diameter = get_diameter_info_from_historical_data(
        results_df, competitor_name, event_code
    )

    # CRITICAL: Check if same-tournament result exists (heats/semis on SAME wood)
    tournament_time = None
    if tournament_results and competitor_name in tournament_results:
        tournament_time = tournament_results[competitor_name]

    # 1. Get baseline prediction using Baseline V2 Hybrid Model
    # Try V2 first, fall back to V1 if unavailable
    from woodchopping.data import load_wood_data
    try:
        wood_df = load_wood_data()

        # Call Baseline V2 Hybrid (with tournament weighting and quality adjustment)
        baseline, confidence, explanation, metadata = predict_baseline_v2_hybrid(
            competitor_name=competitor_name,
            species=species,
            diameter=diameter,
            quality=quality,
            event_code=event_code,
            results_df=results_df,
            wood_df=wood_df,
            tournament_results={competitor_name: tournament_time} if tournament_time else None,
            enable_calibration=True
        )

        # Extract metadata for Monte Carlo simulation
        if metadata:
            predictions['baseline']['std_dev'] = metadata.get('std_dev')
            predictions['baseline']['metadata'] = metadata
            if metadata.get('tournament_weighted', False):
                predictions['baseline']['tournament_weighted'] = True

        # Baseline V2 succeeded
        predictions['baseline']['time'] = baseline
        predictions['baseline']['confidence'] = confidence
        predictions['baseline']['explanation'] = explanation

    except Exception as e:
        # Fall back to V1 baseline (old implementation)
        # Get historical data WITH weights (based on age of result)
        historical_data, data_source, normalization_meta = get_competitor_historical_times_normalized(
            competitor_name, species, diameter, event_code, results_df, return_weights=True
        )

        if len(historical_data) >= 3:
            # Calculate robust weighted mean using time-decay weights
            historical_baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
            event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df)
            if event_baseline is not None and historical_baseline is not None:
                historical_baseline = apply_shrinkage(historical_baseline, effective_n, event_baseline)

            # TOURNAMENT RESULT WEIGHTING: Apply 97% to same-tournament time, 3% to historical
            if tournament_time is not None:
                baseline = (tournament_time * 0.97) + (historical_baseline * 0.03)
                confidence = "VERY HIGH"
                explanation = f"Tournament result ({tournament_time:.2f}s @ 97%) + robust history ({data_source}, {len(historical_data)} results @ 3%)"
                predictions['baseline']['tournament_weighted'] = True
            else:
                baseline = historical_baseline
                confidence = "HIGH"
                explanation = f"Robust time-weighted baseline ({data_source}, {len(historical_data)} results, avg weight {avg_weight:.2f})"

        elif len(historical_data) > 0:
            # Limited history - still use robust weighting but note low confidence
            historical_baseline, avg_weight, effective_n = compute_robust_weighted_mean(historical_data)
            event_baseline, event_source = get_event_baseline_flexible(species, diameter, event_code, results_df)
            if event_baseline is not None and historical_baseline is not None:
                historical_baseline = apply_shrinkage(historical_baseline, effective_n, event_baseline)

            # TOURNAMENT RESULT WEIGHTING even with limited history
            if tournament_time is not None:
                baseline = (tournament_time * 0.97) + (historical_baseline * 0.03)
                confidence = "HIGH"
                explanation = f"Tournament result ({tournament_time:.2f}s @ 97%) + limited robust history ({data_source}, {len(historical_data)} results @ 3%)"
                predictions['baseline']['tournament_weighted'] = True
            else:
                baseline = historical_baseline
                confidence = "MEDIUM"
                explanation = f"Limited robust history ({data_source}, {len(historical_data)} results, avg weight {avg_weight:.2f})"
        else:
            # NO historical data - use tournament time if available, otherwise event baseline
            if tournament_time is not None:
                baseline = tournament_time
                confidence = "HIGH"
                explanation = f"Tournament result ({tournament_time:.2f}s, no historical data)"
                predictions['baseline']['tournament_weighted'] = True
            else:
                baseline, baseline_source = get_event_baseline_flexible(species, diameter, event_code, results_df)
                if baseline:
                    confidence = "LOW"
                    explanation = f"Event baseline ({baseline_source})"
                else:
                    # Ultimate fallback based on diameter
                    if diameter >= 350:
                        baseline = 60.0
                    elif diameter >= 300:
                        baseline = 45.0
                    elif diameter >= 250:
                        baseline = 35.0
                    else:
                        baseline = 30.0
                    confidence = "LOW"
                    explanation = "Default estimate (no history)"

        # Determine quality value (needed for quality adjustment)
        quality_val = int(quality) if quality is not None else 5
        quality_val = max(1, min(10, quality_val))

        # Adjust confidence if normalization required large jumps
        if normalization_meta.get('max_diameter_diff', 0.0) > 25 or normalization_meta.get('species_normalized', False):
            if confidence == "VERY HIGH":
                confidence = "HIGH"
            elif confidence == "HIGH":
                confidence = "MEDIUM"
            elif confidence == "MEDIUM":
                confidence = "LOW"

            explanation = f"{explanation} [Normalized across sizes/species]"
            predictions['baseline']['scaled'] = True
            predictions['baseline']['original_diameter'] = hist_diameter
            max_diff = normalization_meta.get('max_diameter_diff', 0.0)
            if max_diff:
                predictions['baseline']['scaling_warning'] = f"Normalized by size/species (max diff {max_diff:.0f}mm)"
            else:
                predictions['baseline']['scaling_warning'] = "Normalized by size/species"

        # Apply WOOD QUALITY ADJUSTMENT to baseline (V1 only - V2 does this internally)
        if quality_val != 5:
            quality_offset = quality_val - 5
            quality_factor = 1.0 + (quality_offset * 0.02)
            baseline = baseline * quality_factor

            adjustment_pct = (quality_factor - 1.0) * 100
            if quality_val < 5:
                explanation += f" [Quality {quality_val}/10: softer, {adjustment_pct:+.0f}%]"
            else:
                explanation += f" [Quality {quality_val}/10: harder, {adjustment_pct:+.0f}%]"

        predictions['baseline']['time'] = baseline
        predictions['baseline']['confidence'] = confidence
        predictions['baseline']['explanation'] = explanation

    # 2. Get ML prediction
    ml_time, ml_conf, ml_expl = predict_time_ml(
        competitor_name, species, diameter, quality, event_code, results_df
    )

    if ml_time is not None:
        # ML model learns scaling patterns, but flag if historical diameter differs
        if hist_diameter and hist_diameter != diameter:
            ml_conf = adjust_confidence_for_scaling(ml_conf,
                type('obj', (object,), {'confidence_adjustment': 'downgrade' if abs(hist_diameter - diameter) > 25 else ''})())
            ml_expl = f"{ml_expl} [Hist data from {hist_diameter:.0f}mm]"
            predictions['ml']['scaled'] = True
            predictions['ml']['original_diameter'] = hist_diameter
            predictions['ml']['scaling_warning'] = f"Historical data primarily from {hist_diameter:.0f}mm, predicting for {diameter:.0f}mm"

        predictions['ml']['time'] = ml_time
        predictions['ml']['confidence'] = ml_conf
        predictions['ml']['explanation'] = ml_expl
        predictions['ml']['event_code'] = event_code
    else:
        predictions['ml']['error'] = ml_expl if ml_expl else "ML prediction unavailable"

    # 3. Get LLM prediction (with tournament weighting if available)
    llm_time, llm_conf, llm_expl = predict_competitor_time_with_ai(
        competitor_name, species, diameter, quality, event_code, results_df,
        tournament_results={competitor_name: tournament_time} if tournament_time else None
    )

    if llm_time is not None:
        # Mark if tournament weighted
        if tournament_time is not None:
            predictions['llm']['tournament_weighted'] = True

        # LLM uses baseline + quality adjustment, flag diameter mismatch
        if hist_diameter and hist_diameter != diameter:
            llm_conf = adjust_confidence_for_scaling(llm_conf,
                type('obj', (object,), {'confidence_adjustment': 'downgrade' if abs(hist_diameter - diameter) > 25 else ''})())
            llm_expl = f"{llm_expl} [Hist data from {hist_diameter:.0f}mm]"
            predictions['llm']['scaled'] = True
            predictions['llm']['original_diameter'] = hist_diameter
            predictions['llm']['scaling_warning'] = f"Historical data primarily from {hist_diameter:.0f}mm, predicting for {diameter:.0f}mm"

        predictions['llm']['time'] = llm_time
        predictions['llm']['confidence'] = llm_conf
        predictions['llm']['explanation'] = llm_expl
    else:
        predictions['llm']['error'] = "LLM prediction failed"

    return predictions


def select_best_prediction(
    all_predictions: Dict[str, Dict[str, Optional[str]]]
) -> Tuple[float, str, str, str]:
    """
    Select the best prediction from available methods.

    Selection logic:
    - Choose the method with the lowest expected error
    - Expected error uses confidence, scaling penalties, and ML CV MAE when available
    - Tournament-weighted predictions reduce expected error
    - Overall confidence accounts for expected error and method disagreement

    Args:
        all_predictions: dict from get_all_predictions()

    Returns:
        tuple: (predicted_time, method_name, confidence, explanation)

    Example:
        >>> preds = get_all_predictions("John Smith", "WP", 300, 5, "SB")
        >>> time, method, conf, exp = select_best_prediction(preds)
        >>> print(f"Using {method}: {time:.1f}s ({conf})")
    """
    baseline_pred = all_predictions.get('baseline', {})
    ml_pred = all_predictions.get('ml', {})
    llm_pred = all_predictions.get('llm', {})

    def _expected_error(confidence: Optional[str], method: str, pred: dict) -> float:
        base_map = {
            'VERY HIGH': 2.0,
            'HIGH': 3.0,
            'MEDIUM': 5.0,
            'LOW': 7.0,
            'VERY LOW': 9.0
        }
        base = base_map.get(confidence or 'LOW', 7.0)

        if method == 'ML':
            # Prefer using CV MAE if available
            event_code = pred.get('event_code')
            cv_metrics = get_model_cv_metrics(event_code) if event_code else None
            if cv_metrics and 'mae_mean' in cv_metrics:
                base = max(base, float(cv_metrics['mae_mean']))

        if method == 'LLM':
            base += 0.5  # Slight penalty for variance

        if pred.get('scaled'):
            base += 1.5

        if pred.get('tournament_weighted'):
            base = max(0.5, base - 1.0)

        return base

    def _confidence_from_error(err: float) -> str:
        if err <= 2.5:
            return 'VERY HIGH'
        if err <= 3.5:
            return 'HIGH'
        if err <= 5.5:
            return 'MEDIUM'
        if err <= 7.5:
            return 'LOW'
        return 'VERY LOW'

    def _downgrade_confidence(conf: str, steps: int) -> str:
        order = ['VERY HIGH', 'HIGH', 'MEDIUM', 'LOW', 'VERY LOW']
        if conf not in order:
            return conf
        idx = min(len(order) - 1, order.index(conf) + steps)
        return order[idx]

    candidates = []
    if ml_pred.get('time') is not None:
        ml_pred = dict(ml_pred)
        ml_pred['event_code'] = ml_pred.get('event_code')
        candidates.append((
            ml_pred['time'], 'ML', ml_pred.get('confidence'), ml_pred.get('explanation'), _expected_error(ml_pred.get('confidence'), 'ML', ml_pred)
        ))
    if llm_pred.get('time') is not None:
        candidates.append((
            llm_pred['time'], 'LLM', llm_pred.get('confidence'), llm_pred.get('explanation'), _expected_error(llm_pred.get('confidence'), 'LLM', llm_pred)
        ))
    if baseline_pred.get('time') is not None:
        candidates.append((
            baseline_pred['time'], 'Baseline', baseline_pred.get('confidence'), baseline_pred.get('explanation'), _expected_error(baseline_pred.get('confidence'), 'Baseline', baseline_pred)
        ))

    if not candidates:
        return (0.0, 'Baseline', 'LOW', 'Default baseline')

    # Choose method with lowest expected error
    best = min(candidates, key=lambda x: x[4])

    # Overall confidence: expected error + disagreement penalty
    candidate_times = [c[0] for c in candidates if c[0] is not None]
    spread_penalty = 0
    if len(candidate_times) >= 2:
        mean_time = sum(candidate_times) / len(candidate_times)
        max_diff = max(candidate_times) - min(candidate_times)
        pct_diff = max_diff / mean_time if mean_time else 0.0
        if max_diff >= 6.0 or pct_diff >= 0.25:
            spread_penalty = 2
        elif max_diff >= 4.0 or pct_diff >= 0.12:
            spread_penalty = 1

    selection_conf = _confidence_from_error(best[4])
    if spread_penalty:
        selection_conf = _downgrade_confidence(selection_conf, spread_penalty)

    # Preserve method-level confidence detail in explanation when it differs
    method_conf = best[2] or "LOW"
    explanation = best[3]
    if method_conf != selection_conf and explanation:
        explanation = f"{explanation} [Method conf: {method_conf}, overall conf: {selection_conf}]"

    return best[0], best[1], selection_conf, explanation


def _generate_statistical_prediction_analysis(
    all_competitors_predictions: List[Dict],
    wood_selection: Dict
) -> str:
    """
    Generate statistical prediction analysis when LLM is unavailable.

    Calculates agreement statistics, identifies discrepancies, and provides
    actionable recommendations based on pure numerical analysis.

    Args:
        all_competitors_predictions: List of competitor prediction dicts
        wood_selection: Wood characteristics dict

    Returns:
        str: Formatted statistical analysis report
    """
    from woodchopping.data import get_species_name_from_code

    # Calculate statistics
    total_competitors = len(all_competitors_predictions)
    ml_llm_diffs = []
    baseline_ml_diffs = []
    baseline_llm_diffs = []
    high_discrepancy_competitors = []
    strong_agreement_competitors = []

    for comp_pred in all_competitors_predictions:
        name = comp_pred['name']
        baseline = comp_pred['predictions']['baseline']['time']
        ml = comp_pred['predictions']['ml']['time']
        llm = comp_pred['predictions']['llm']['time']

        if ml and llm:
            ml_llm_diff = abs(ml - llm)
            ml_llm_diffs.append(ml_llm_diff)

            # Check for high discrepancy (>20% or >5 seconds)
            max_time = max(ml, llm)
            if ml_llm_diff > 5 or (ml_llm_diff / max_time > 0.20):
                high_discrepancy_competitors.append((name, baseline, ml, llm, ml_llm_diff))

            # Check for strong agreement (<5% difference)
            if ml_llm_diff / max_time < 0.05:
                strong_agreement_competitors.append(name)

        if baseline and ml:
            baseline_ml_diffs.append(abs(baseline - ml))

        if baseline and llm:
            baseline_llm_diffs.append(abs(baseline - llm))

    # Calculate average differences
    avg_ml_llm_diff = sum(ml_llm_diffs) / len(ml_llm_diffs) if ml_llm_diffs else 0
    avg_baseline_ml_diff = sum(baseline_ml_diffs) / len(baseline_ml_diffs) if baseline_ml_diffs else 0
    avg_baseline_llm_diff = sum(baseline_llm_diffs) / len(baseline_llm_diffs) if baseline_llm_diffs else 0

    # Get species name
    species_code = wood_selection.get('species', 'Unknown')
    species_name = get_species_name_from_code(species_code)
    quality = wood_selection.get('quality', 5)

    # Build report
    report = f"""PREDICTION METHOD ANALYSIS (Statistical Summary)

WOOD CHARACTERISTICS:
- Species: {species_name}
- Diameter: {wood_selection.get('size_mm', 0)}mm
- Quality: {quality}/10
- Event: {wood_selection.get('event', 'Unknown')}

OVERALL AGREEMENT:
The prediction methods show {"strong" if avg_ml_llm_diff < 2 else "moderate" if avg_ml_llm_diff < 4 else "weak"} agreement across {total_competitors} competitors.

- Average ML vs LLM difference: {avg_ml_llm_diff:.1f} seconds
- Average Baseline vs ML difference: {avg_baseline_ml_diff:.1f} seconds
- Average Baseline vs LLM difference: {avg_baseline_llm_diff:.1f} seconds

{"Strong agreement competitors (" + str(len(strong_agreement_competitors)) + "): All methods within 5% - high confidence in these predictions." if strong_agreement_competitors else ""}

{"HIGH DISCREPANCY COMPETITORS:" if high_discrepancy_competitors else ""}"""

    if high_discrepancy_competitors:
        report += "\nThe following competitors show significant differences between prediction methods (>20% or >5 seconds):\n"
        for name, baseline, ml, llm, diff in high_discrepancy_competitors[:5]:
            report += f"\n- {name}: Baseline={baseline:.1f}s, ML={ml:.1f}s, LLM={llm:.1f}s (diff={diff:.1f}s)"
            if ml and llm:
                pct_diff = (diff / max(ml, llm)) * 100
                report += f" ({pct_diff:.0f}% difference)"

    report += f"""

DISCREPANCY EXPLANATIONS:
- Baseline vs ML differences typically reflect wood characteristics (species, diameter) not fully captured in historical averages
- LLM vs ML differences typically reflect quality adjustments - Quality {quality} {"increases" if quality > 5 else "decreases" if quality < 5 else "does not affect"} predicted times
- Large discrepancies (>20%) suggest limited historical data or unusual wood characteristics for that competitor

DATA QUALITY ASSESSMENT:
- {len(strong_agreement_competitors)} competitors have strong data (all methods agree within 5%)
- {len(high_discrepancy_competitors)} competitors have uncertain data (methods disagree significantly)
- Review confidence levels shown in the main handicap table for per-competitor reliability

RECOMMENDATIONS:
{"- Review the " + str(len(high_discrepancy_competitors)) + " competitors listed above - consider manual adjustment if predictions seem unrealistic" if high_discrepancy_competitors else "- No major discrepancies detected - predictions are consistent"}
- Pay special attention to competitors with LOW or MEDIUM confidence ratings
- {"Quality " + str(quality) + " wood may disproportionately affect slower competitors - verify fairness via Monte Carlo simulation" if quality != 5 else "Quality 5 (average) wood should minimize wood-related biases"}
- Overall confidence in handicap marks: {"HIGH" if avg_ml_llm_diff < 2 and len(high_discrepancy_competitors) < 2 else "MEDIUM" if avg_ml_llm_diff < 4 else "REVIEW RECOMMENDED"}

(Note: AI analysis unavailable - statistical summary provided)"""

    return report


def generate_prediction_analysis_llm(
    all_competitors_predictions: List[Dict],
    wood_selection: Dict
) -> str:
    """
    Use LLM to analyze differences between ML and LLM predictions across all competitors.

    Args:
        all_competitors_predictions: list of dicts with competitor predictions
            [
                {
                    'name': str,
                    'predictions': {
                        'baseline': {...},
                        'ml': {...},
                        'llm': {...}
                    }
                },
                ...
            ]
        wood_selection: dict with wood characteristics
            {
                'species': str,
                'size_mm': float,
                'quality': int,
                'event': str
            }

    Returns:
        str: Natural language analysis of prediction differences

    Example:
        >>> analysis = generate_prediction_analysis_llm(predictions, wood_info)
        >>> print(analysis)
    """
    # Note: Removed wasteful test call - just try the actual call and handle failure

    # Build concise summary for LLM
    summary_lines = []
    for comp_pred in all_competitors_predictions[:10]:  # Limit to 10 for prompt size
        name = comp_pred['name'][:20]  # Truncate long names
        baseline = comp_pred['predictions']['baseline']['time']
        ml = comp_pred['predictions']['ml']['time']
        llm = comp_pred['predictions']['llm']['time']

        if ml and llm:
            ml_llm_diff = ml - llm
            summary_lines.append(f"{name}: Baseline={baseline:.1f}s, ML={ml:.1f}s, LLM={llm:.1f}s (diff={ml_llm_diff:+.1f}s)")
        elif ml:
            summary_lines.append(f"{name}: Baseline={baseline:.1f}s, ML={ml:.1f}s, LLM=N/A")
        elif llm:
            summary_lines.append(f"{name}: Baseline={baseline:.1f}s, ML=N/A, LLM={llm:.1f}s")

    summary_text = "\n".join(summary_lines)

    # Get species name from code
    from woodchopping.data import get_species_name_from_code
    species_code = wood_selection.get('species', 'Unknown')
    species_name = get_species_name_from_code(species_code)

    prompt = f"""You are an expert woodchopping handicapping consultant analyzing prediction methods.

WOOD CHARACTERISTICS:
- Species: {species_name}
- Diameter: {wood_selection.get('size_mm', 0)}mm
- Quality: {wood_selection.get('quality', 5)}/10
- Event: {wood_selection.get('event', 'Unknown')}

PREDICTION DATA (Baseline / ML / LLM):
{summary_text}

ANALYSIS REQUIRED (provide detailed, technical assessment in 15-20 sentences):

1. OVERALL AGREEMENT:
   - How closely do the three methods agree?
   - What is the typical prediction spread?
   - Are there any concerning outliers?

2. METHOD SELECTION REASONING:
   For competitors where methods differed significantly (>15%):
   - Which method was chosen and why?
   - What makes that method most reliable for this competitor?
   - Are there data quality or availability factors?

3. DISCREPANCY EXPLANATIONS:
   - Why might Baseline differ from ML? (e.g., wood characteristics not captured in history)
   - Why might LLM differ from ML? (e.g., quality adjustment vs historical patterns)
   - Which discrepancies are expected vs concerning?

4. DATA QUALITY ASSESSMENT:
   - Which competitors have strong data (all methods agree)?
   - Which have weak/uncertain data (methods disagree)?
   - How should judges interpret confidence levels?

5. RECOMMENDATIONS:
   - Should judges review any specific predictions before approving?
   - Are there competitors where manual adjustment might be warranted?
   - Overall confidence in these handicap marks?

Provide specific data references and technical reasoning."""

    from config import llm_config
    response = call_ollama(prompt, model=llm_config.DEFAULT_MODEL, num_predict=llm_config.TOKENS_PREDICTION_ANALYSIS)

    if response:
        return response
    else:
        # Fallback: Generate statistical summary without AI
        return _generate_statistical_prediction_analysis(all_competitors_predictions, wood_selection)


def calculate_percentage_differences(handicap_results: List[Dict]) -> List[Dict]:
    """
    Calculate percentage differences between all prediction method pairs.

    Args:
        handicap_results: List of competitor results with predictions

    Returns:
        List of dicts with percentage differences for each competitor:
        {
            'name': str,
            'mark': int,
            'used_time': float,
            'baseline_vs_ml': float,
            'baseline_vs_llm': float,
            'ml_vs_baseline': float,
            'ml_vs_llm': float,
            'llm_vs_baseline': float,
            'llm_vs_ml': float,
            'baseline_time': float or None,
            'ml_time': float or None,
            'llm_time': float or None
        }
    """
    differences = []

    for result in handicap_results:
        name = result['name']
        mark = result['mark']
        predictions = result['predictions']

        baseline_time = predictions['baseline']['time']
        ml_time = predictions['ml']['time']
        llm_time = predictions['llm']['time']

        # Calculate percentage differences in both directions
        diff = {
            'name': name,
            'mark': mark,
            'used_time': result['predicted_time'],
            'baseline_time': baseline_time,
            'ml_time': ml_time,
            'llm_time': llm_time,
            'baseline_vs_ml': None,
            'baseline_vs_llm': None,
            'ml_vs_baseline': None,
            'ml_vs_llm': None,
            'llm_vs_baseline': None,
            'llm_vs_ml': None
        }

        # Baseline vs ML
        if baseline_time and ml_time:
            diff['baseline_vs_ml'] = ((baseline_time - ml_time) / ml_time) * 100
            diff['ml_vs_baseline'] = ((ml_time - baseline_time) / baseline_time) * 100

        # Baseline vs LLM
        if baseline_time and llm_time:
            diff['baseline_vs_llm'] = ((baseline_time - llm_time) / llm_time) * 100
            diff['llm_vs_baseline'] = ((llm_time - baseline_time) / baseline_time) * 100

        # ML vs LLM
        if ml_time and llm_time:
            diff['ml_vs_llm'] = ((ml_time - llm_time) / llm_time) * 100
            diff['llm_vs_ml'] = ((llm_time - ml_time) / ml_time) * 100

        differences.append(diff)

    return differences


def display_percentage_differences_table(differences: List[Dict]) -> None:
    """
    Display table of percentage differences between prediction methods.

    Args:
        differences: List from calculate_percentage_differences()
    """
    print("\n" + "="*110)
    print("PREDICTION DIFFERENCES BY COMPETITOR")
    print("="*110)

    # Header
    print(f"{'Competitor':<25} {'Mark':>4} {'Used':>6} | {'Baseline':<8} | {'ML Model':<8} | {'LLM Model':<8}")
    print(f"{'':<25} {'':<4} {'Time':>6} | {'vs ML':>8} {'vs LLM':>8} | {'vs Base':>8} {'vs LLM':>8} | {'vs Base':>8} {'vs ML':>8}")
    print("-"*110)

    for diff in differences:
        name = diff['name'][:24]  # Truncate if too long
        mark = diff['mark']
        used_time = diff['used_time']

        # Format percentage differences, showing N/A if not available
        base_ml = f"{diff['baseline_vs_ml']:+.1f}%" if diff['baseline_vs_ml'] is not None else "  N/A  "
        base_llm = f"{diff['baseline_vs_llm']:+.1f}%" if diff['baseline_vs_llm'] is not None else "  N/A  "
        ml_base = f"{diff['ml_vs_baseline']:+.1f}%" if diff['ml_vs_baseline'] is not None else "  N/A  "
        ml_llm = f"{diff['ml_vs_llm']:+.1f}%" if diff['ml_vs_llm'] is not None else "  N/A  "
        llm_base = f"{diff['llm_vs_baseline']:+.1f}%" if diff['llm_vs_baseline'] is not None else "  N/A  "
        llm_ml = f"{diff['llm_vs_ml']:+.1f}%" if diff['llm_vs_ml'] is not None else "  N/A  "

        # Highlight large discrepancies (>20%)
        warnings = []
        if diff['baseline_vs_ml'] and abs(diff['baseline_vs_ml']) > 20:
            warnings.append("[WARN]")
        if diff['baseline_vs_llm'] and abs(diff['baseline_vs_llm']) > 20:
            warnings.append("[WARN]")
        if diff['ml_vs_llm'] and abs(diff['ml_vs_llm']) > 20:
            warnings.append("[WARN]")

        warning_str = "".join(warnings) if warnings else ""

        print(f"{name:<25} {mark:>4} {used_time:>5.1f}s | {base_ml:>8} {base_llm:>8} | {ml_base:>8} {ml_llm:>8} | {llm_base:>8} {llm_ml:>8} {warning_str}")

    print("="*110)
    print("[WARN] = Difference >20% (significant discrepancy - review recommended)")
    print()


def display_methods_explanation(ml_training_info: Dict = None) -> None:
    """
    Display comprehensive explanation of all three prediction methods.

    Args:
        ml_training_info: Optional dict with ML model training stats
                         {'mae': float, 'r2': float, 'training_records': int}
    """
    print("\n" + "="*70)
    print("PREDICTION METHODS EXPLAINED")
    print("="*70)

    print("\nBASELINE (Statistical):")
    print("  - Time-decay weighted historical average (730-day half-life)")
    print("  - Normalizes historical times to target size/species")
    print("  - Cascading fallback: competitor exact match -> mixed species -> event average")
    print("  - Strengths: Always available, uses actual performance data")
    print("  - Limitations: Quality data is sparse; normalization assumes quality=5 when missing")

    print("\nML MODEL (XGBoost):")
    if ml_training_info:
        print(f"  - Trained on {ml_training_info.get('training_records', 'N/A')} historical performances")
        print(f"  - Model Performance: MAE={ml_training_info.get('mae', 0):.1f}s, R²={ml_training_info.get('r2', 0):.3f}")
    else:
        print("  - Machine learning model trained on historical data")
    print("  - Features: competitor history, wood hardness, density, diameter, experience")
    print("  - Strengths: Learns complex patterns, accounts for wood characteristics")
    print("  - Limitations: Requires sufficient training data (80+ records minimum)")

    print("\nLLM (AI Quality Adjustment):")
    print("  - Ollama qwen2.5:7b with wood quality reasoning")
    print("  - Combines statistical baseline with AI quality assessment")
    print("  - Strengths: Considers wood quality nuances, flexible reasoning")
    print("  - Limitations: Requires Ollama running, may vary from historical patterns")

    print("\nSELECTION LOGIC: Lowest expected error wins")
    print("  ?+' Uses confidence, scaling penalties, and CV MAE (ML) when available")
    print("  ?+' Methods can change per competitor based on data quality")
    print("  ?+' Baseline remains a safe fallback when data are sparse")
    print("="*70)
    print()


def display_selection_reasoning(handicap_results: List[Dict], differences: List[Dict]) -> None:
    """
    Display detailed reasoning for why each method was selected for each competitor.

    Args:
        handicap_results: List of competitor results with predictions
        differences: List from calculate_percentage_differences()
    """
    print("\n" + "="*70)
    print("METHOD SELECTION DETAILS")
    print("="*70)
    print()

    for result, diff in zip(handicap_results, differences):
        name = result['name']
        mark = result['mark']
        method_used = result['method_used']
        confidence = result['confidence']
        predictions = result['predictions']

        print(f"{name} (Mark {mark}) - {method_used} Selected:")

        # Get prediction times
        base_time = predictions['baseline']['time']
        ml_time = predictions['ml']['time']
        llm_time = predictions['llm']['time']

        # Check for large discrepancies
        has_large_discrepancy = False
        discrepancy_details = []

        if diff['baseline_vs_ml'] and abs(diff['baseline_vs_ml']) > 20:
            has_large_discrepancy = True
            discrepancy_details.append(f"Baseline={base_time:.1f}s vs ML={ml_time:.1f}s ({diff['baseline_vs_ml']:+.1f}% difference)")

        if diff['baseline_vs_llm'] and abs(diff['baseline_vs_llm']) > 20:
            has_large_discrepancy = True
            discrepancy_details.append(f"Baseline={base_time:.1f}s vs LLM={llm_time:.1f}s ({diff['baseline_vs_llm']:+.1f}% difference)")

        if diff['ml_vs_llm'] and abs(diff['ml_vs_llm']) > 20:
            has_large_discrepancy = True
            discrepancy_details.append(f"ML={ml_time:.1f}s vs LLM={llm_time:.1f}s ({diff['ml_vs_llm']:+.1f}% difference)")

        # Display reasoning based on method and situation
        if method_used == "ML":
            if ml_time:
                print(f"  [OK] ML available with {confidence} confidence")
                print(f"  [OK] {predictions['ml']['explanation']}")
            if has_large_discrepancy:
                print(f"  [WARN] Large discrepancy detected:")
                for detail in discrepancy_details:
                    print(f"    - {detail}")
                print(f"  -> ML chosen - judge should verify this prediction")
            else:
                if base_time and abs((ml_time - base_time) / base_time * 100) < 15:
                    print(f"  [OK] All methods agree within 15% (good data quality)")
                print(f"  -> ML chosen (lowest expected error)")

        elif method_used == "LLM":
            print(f"  [OK] LLM available with {confidence} confidence")
            print(f"  [OK] {predictions['llm']['explanation']}")
            if ml_time is None:
                print(f"  ? ML not available")
            if has_large_discrepancy:
                print(f"  [WARN] Large discrepancy detected:")
                for detail in discrepancy_details:
                    print(f"    - {detail}")
            print(f"  -> LLM chosen (lowest expected error)")

        elif method_used == "Baseline":
            print(f"  [OK] Baseline available with {confidence} confidence")
            print(f"  [OK] {predictions['baseline']['explanation']}")
            if ml_time is None and llm_time is None:
                print(f"  ? ML and LLM not available")
            if has_large_discrepancy:
                print(f"  [WARN] Large discrepancy among predictions")
            print(f"  -> Baseline chosen (lowest expected error)")

        print()

    print("="*70)
    print()


def display_comprehensive_prediction_analysis(
    handicap_results: List[Dict],
    wood_selection: Dict,
    ml_training_info: Dict = None
) -> None:
    """
    Display comprehensive analysis of all prediction methods.

    This is the complete Phase 3 analysis that shows after Monte Carlo simulation.
    Includes:
    1. Methods explanation
    2. Percentage differences table
    3. Method selection reasoning
    4. Detailed AI analysis (5 sections)

    Args:
        handicap_results: List of competitor results with predictions
        wood_selection: Wood characteristics dict
        ml_training_info: Optional ML model training stats
    """
    # 1. Explain the three methods
    display_methods_explanation(ml_training_info)

    # 2. Show percentage differences
    differences = calculate_percentage_differences(handicap_results)
    display_percentage_differences_table(differences)

    # 3. Show selection reasoning
    display_selection_reasoning(handicap_results, differences)

    # 4. Generate and display comprehensive AI analysis
    print("\n" + "="*70)
    print("AI ANALYSIS OF PREDICTIONS")
    print("="*70)
    print("\nAnalyzing prediction methods and discrepancies...")

    try:
        analysis = generate_prediction_analysis_llm(handicap_results, wood_selection)

        # Use format_ai_assessment for better formatting
        from woodchopping.simulation.fairness import format_ai_assessment
        print("")
        format_ai_assessment(analysis, width=100)
    except Exception as e:
        print(f"\n[WARN] Error generating AI analysis: {e}")
        print("This is likely due to Ollama timeout or connection issues.")
        print("Try increasing the timeout in config.py or check if Ollama is running properly.")

    print("="*70)
    print()


def display_basic_prediction_table(
    handicap_results: List[Dict],
    wood_selection: Dict
) -> None:
    """
    Display basic prediction table for Phase 1 (initial display before Monte Carlo).

    Shows handicap marks with side-by-side predictions, but not the comprehensive analysis.

    Args:
        handicap_results: List of competitor results with predictions
        wood_selection: Wood characteristics dict
    """
    # Show wood info
    print("\n" + "="*70)
    print(f"  HANDICAP MARKS - {wood_selection.get('event', 'Unknown Event')}")
    print("="*70)
    species_code = wood_selection.get('species', 'Unknown')
    size = wood_selection.get('size_mm', 0)
    quality = wood_selection.get('quality', 5)

    # Get species name from code
    from woodchopping.data import get_species_name_from_code
    species_name = get_species_name_from_code(species_code)

    print(f"Wood: {species_name} | Diameter: {size}mm | Quality: {quality}/10")
    print()

    # Show prediction table
    print(f"{'Competitor':<25} {'Mark':>4} | {'Baseline':>10} | {'ML':>10} | {'LLM':>10} | {'Used':>8} | {'Warnings'}")
    print("-"*110)

    warnings_to_show = []

    for result in handicap_results:
        name = result['name'][:24]
        mark = result['mark']
        predictions = result['predictions']

        # Get times or show N/A
        baseline_time = predictions['baseline']['time']
        ml_time = predictions['ml']['time']
        llm_time = predictions['llm']['time']

        baseline_str = f"{baseline_time:.1f}s" if baseline_time else "N/A"
        ml_str = f"{ml_time:.1f}s" if ml_time else "N/A"
        llm_str = f"{llm_time:.1f}s" if llm_time else "N/A"

        method_used = result['method_used']

        # Check for scaling warnings
        warning_flags = []
        method_pred = predictions.get(method_used.lower(), {})

        if method_pred.get('scaled', False):
            orig_diam = method_pred.get('original_diameter')
            if orig_diam:
                warning_flags.append(f"Scaled from {orig_diam:.0f}mm")

        # Check if no historical data (confidence is LOW and explanation mentions baseline)
        if method_pred.get('confidence') == 'LOW' and 'baseline' in method_pred.get('explanation', '').lower():
            if 'no history' in method_pred.get('explanation', '').lower():
                warning_flags.append("No UH data")

        warnings_str = ", ".join(warning_flags) if warning_flags else ""

        print(f"{name:<25} {mark:>4} | {baseline_str:>10} | {ml_str:>10} | {llm_str:>10} | {method_used:>8} | {warnings_str}")

        # Collect detailed warnings for end display
        if method_pred.get('scaling_warning'):
            warnings_to_show.append(f"  - {name}: {method_pred['scaling_warning']}")

    print("="*110)

    # Show detailed warnings if any
    if warnings_to_show:
        print("\nWARNINGS - Predictions based on different wood sizes:")
        for warning in warnings_to_show:
            print(warning)

    print()


def display_handicap_calculation_explanation() -> None:
    """
    Display explanation of how handicap marks are calculated from predicted times.

    This is shown in Phase 4 if requested by judge.
    """
    print("\n" + "="*70)
    print("HOW HANDICAP MARKS ARE CALCULATED")
    print("="*70)

    print("\nMARK ASSIGNMENT RULES:")
    print("  1. Slowest predicted competitor receives Mark 3 (front marker)")
    print("  2. Each second faster increases mark by 1")
    print("  3. Fastest predicted competitor receives highest mark (back marker)")
    print("  4. Marks are rounded UP to whole seconds")
    print("  5. Maximum time limit: 180 seconds (AAA rules)")

    print("\nEXAMPLE:")
    print("  Competitor A: Predicted 60.0s -> Mark 3 (slowest, starts first)")
    print("  Competitor B: Predicted 55.0s -> Mark 8 (5 seconds faster)")
    print("  Competitor C: Predicted 50.0s -> Mark 13 (10 seconds faster)")

    print("\nGOAL:")
    print("  All competitors should theoretically finish at the same time")
    print("  Front markers (low marks) get head start")
    print("  Back markers (high marks) start later to compensate for skill")

    print("\nPREDICTION METHOD SELECTION:")
    print("  The method with the lowest expected error is used")
    print("  Confidence, scaling penalties, and CV MAE influence the choice")
    print("  Different competitors may use different methods")

    print("="*70)
    print()


def display_dual_predictions(
    handicap_results: List[Dict],
    wood_selection: Dict
) -> None:
    """
    Display handicap marks with all three prediction methods side-by-side.

    Args:
        handicap_results: List of dicts from calculate_ai_enhanced_handicaps()
            [
                {
                    'name': str,
                    'mark': int,
                    'predictions': {
                        'baseline': {...},
                        'ml': {...},
                        'llm': {...}
                    },
                    'method_used': str
                },
                ...
            ]
        wood_selection: Dict with wood characteristics

    Shows:
        - Competitor name
        - Handicap mark
        - Baseline prediction
        - ML prediction
        - LLM prediction
        - Method used for marks
        - Summary of methods
        - Optional AI analysis of differences
    """
    if not handicap_results:
        print("No handicap results to display")
        return

    # Sort by mark (ascending)
    sorted_results = sorted(handicap_results, key=lambda x: x['mark'])

    # Build header
    print("\n" + "=" * 110)
    wood_info = f"{wood_selection.get('species', 'Unknown')}, {wood_selection.get('size_mm', 0)}mm, Quality: {wood_selection.get('quality', 5)}"
    print(f"HANDICAP MARKS - {wood_info}")
    print("=" * 110)

    # Column headers
    print(f"\n{'Competitor Name':<35} {'Mark':>4}  {'Baseline':>9}  {'ML Model':>9}  {'LLM Model':>9}  {'Used':<8}")
    print("-" * 110)

    # Count methods available
    ml_available_count = 0
    llm_available_count = 0
    method_counts = {'Baseline': 0, 'ML': 0, 'LLM': 0}

    # Display each competitor
    for comp in sorted_results:
        name = comp['name'][:35]
        mark = comp['mark']

        # Get predictions
        baseline_time = comp['predictions']['baseline']['time']
        ml_time = comp['predictions']['ml']['time']
        llm_time = comp['predictions']['llm']['time']

        # Format predictions (show "N/A" if None)
        baseline_str = f"{baseline_time:.1f}s" if baseline_time else "N/A"
        ml_str = f"{ml_time:.1f}s" if ml_time else "N/A"
        llm_str = f"{llm_time:.1f}s" if llm_time else "N/A"

        # Track which method was used
        method_used = comp.get('method_used', 'Unknown')
        method_counts[method_used] = method_counts.get(method_used, 0) + 1

        # Count availability
        if ml_time is not None:
            ml_available_count += 1
        if llm_time is not None:
            llm_available_count += 1

        print(f"{name:<35} {mark:4d}  {baseline_str:>9}  {ml_str:>9}  {llm_str:>9}  {method_used:<8}")

    print("=" * 110)

    # Display prediction methods summary
    print("\nPrediction Methods Summary:")
    print(f"  - Baseline: Statistical calculation (always available)")

    if ml_available_count > 0:
        ml_status = "HIGH" if _model_training_data_size >= 80 else "MEDIUM" if _model_training_data_size >= 50 else "LOW"
        print(f"  - ML Model: XGBoost trained on {_model_training_data_size} records [CONFIDENCE: {ml_status}] - Available for {ml_available_count}/{len(sorted_results)} competitors")
    else:
        print(f"  - ML Model: Not available (insufficient training data)")

    if llm_available_count > 0:
        print(f"  - LLM Model: Ollama qwen2.5:7b AI prediction - Available for {llm_available_count}/{len(sorted_results)} competitors")
    else:
        print(f"  - LLM Model: Not available (Ollama not running or prediction failed)")

    # Show which method was primarily used
    primary_method = max(method_counts, key=method_counts.get)
    print(f"\nMarks calculated using: {primary_method} predictions")
    print("(Selection uses lowest expected error, not a fixed priority)")

    # Offer AI analysis
    print("\n" + "=" * 110)
    analyze = input("\nPress Enter to see AI analysis of prediction differences (or 'n' to skip): ").strip().lower()

    if analyze != 'n':
        print("\n" + "=" * 110)
        print("AI ANALYSIS OF PREDICTIONS")
        print("=" * 110)
        print("\nAnalyzing prediction differences...")

        analysis = generate_prediction_analysis_llm(handicap_results, wood_selection)

        # Word wrap the analysis for better readability
        wrapped_lines = textwrap.wrap(analysis, width=106)
        for line in wrapped_lines:
            print(line)

        print("\n" + "=" * 110)
