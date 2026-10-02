# LLM Prompt Audit Report
**Date**: January 12, 2026
**System Version**: 5.0
**Audit Purpose**: Review LLM prompts for alignment with current system features and identify improvement opportunities

---

## Executive Summary

Your STRATHEX system has evolved significantly with advanced features like:
- **Baseline V2 Hybrid Model** (hierarchical regression, adaptive time-decay, convergence calibration)
- **Tournament Result Weighting** (97% same-tournament data, critical V4.4 feature)
- **QAA Empirical Scaling** (150+ years validated Australian data)
- **Championship Simulator** (NEW V5.0 with individual competitor statistics)
- **Multi-Event Tournaments** (independent event management)
- **Bracket Tournaments** (single/double elimination with AI seeding)

However, **your LLM prompts haven't been updated to reflect these advances**. This audit identifies gaps where system capabilities aren't communicated to the AI, limiting its reasoning quality and contextual awareness.

**Audit Result**: 🟡 **MODERATE ALIGNMENT** - Core functionality communicated, but missing critical context for advanced features.

---

## Prompt 1: Time Prediction Prompt

**Location**: [woodchopping/predictions/ai_predictor.py:168-336](../../woodchopping/predictions/ai_predictor.py#L168-L336)
**Purpose**: Predicts competitor cutting times with wood quality adjustments
**Model**: `qwen2.5:32b` (32 billion parameters)
**Token Limit**: 50 tokens (fast single-number predictions)

### Current Context Provided ✅

| Context Element | Status | Details |
|-----------------|--------|---------|
| Competitor baseline time | ✅ Good | Passes calculated baseline |
| Data source description | ✅ Good | Explains where baseline came from |
| Confidence level | ✅ Good | HIGH/MEDIUM/LOW based on data quantity |
| Wood specifications | ✅ Excellent | Species, diameter, quality (1-10), event type |
| Wood characteristics database | ✅ Excellent | Full species database with hardness categories |
| Quality rating system | ✅ Excellent | Detailed 1-10 scale with multiplier ranges |
| Expected multiplier ranges | ✅ Good | Provides target ranges per quality level |
| Diameter/quality interaction | ✅ Good | Explains volume calculation implications |

### Missing Critical Context 🔴

#### 1. **Tournament Result Weighting (97% Same-Tournament Data)**
**System Feature**: V4.4 critical enhancement - when `tournament_results` parameter is passed, same-tournament times are weighted at 97% vs historical (3%).

**Current Prompt Status**: ❌ **NOT MENTIONED AT ALL**

**Impact**: When LLM receives a baseline that includes tournament weighting, it has no idea why the baseline is so heavily influenced by one recent result. This can lead to:
- Confusion about why baseline differs from historical average
- Inappropriate quality adjustments (trying to "fix" what's already highly accurate)
- Loss of confidence signal (LLM doesn't know this is VERY HIGH confidence data)

**Evidence from Code**:
```python
# Line 814-828 in ai_predictor.py
if tournament_results and competitor_name in tournament_results:
    tournament_time = tournament_results[competitor_name]
    # 97% tournament, 3% historical
    predicted_time = (tournament_time * 0.97) + (fallback_pred * 0.03)
    confidence = "VERY HIGH"
    explanation = f"Tournament result ({tournament_time:.1f}s) weighted 97%, historical baseline 3%"
```

**Recommendation**: Add tournament context section to prompt when `tournament_results` is present.

---

#### 2. **Time-Decay Weighting Details (Adaptive Half-Lives)**
**System Feature**: Baseline V2 uses **adaptive time-decay** with three different half-lives based on competitor activity:
- Active competitors (5+ results in last 2 years): **365-day half-life**
- Moderate activity: **730-day half-life**
- Inactive competitors: **1095-day half-life**

**Current Prompt Status**: ⚠️ **MENTIONED VAGUELY** but not explained

Current line (179-180):
```
Baseline Time: {baseline:.1f} seconds
Data Source: {explanation_source}
```

**Impact**: LLM doesn't know:
- Why recent performances are weighted so much higher
- That aging competitors' predictions prioritize current form over peak from years ago
- The sophisticated adaptive system behind the baseline calculation

**Evidence from Code**:
```python
# From baseline.py lines 228-247 (baseline_v2_config)
HALF_LIFE_ACTIVE_DAYS: int = 365    # For active competitors
HALF_LIFE_MODERATE_DAYS: int = 730  # Standard 2-year
HALF_LIFE_INACTIVE_DAYS: int = 1095 # Preserve old data longer
```

**Recommendation**: Add adaptive time-decay explanation section.

---

#### 3. **Baseline V2 Hybrid Model Architecture**
**System Feature**: Your baseline calculation is now a **sophisticated hierarchical regression model** with:
- Log-time regression with event/diameter/wood hardness/selection bias features
- Competitor-specific random effects with Empirical Bayes shrinkage
- Data-driven wood hardness index (learned from 6+ wood properties)
- Diameter curve fitting (polynomial log-space)
- Selection bias correction (median diameter as skill proxy)
- Convergence calibration layer (minimizes finish-time spread)

**Current Prompt Status**: ❌ **BASELINE TREATED AS SIMPLE AVERAGE**

Current assumption (line 184-186):
```
BASELINE INTERPRETATION:
- This baseline assumes QUALITY 5 wood (average hardness)
- Your task is to adjust this baseline for the ACTUAL quality rating
```

**Impact**: LLM treats baseline as naive average, not understanding:
- The sophisticated model already accounts for many factors
- Quality adjustment is the ONLY remaining factor to optimize
- Baseline already includes species hardness effects from wood database
- Predictions are convergence-calibrated for handicapping fairness

**Evidence from Code**:
```python
# From baseline.py lines 1891-1907 (predict_baseline_v2_hybrid)
log_pred = (
    intercept +
    (event_intercept_uh * event_is_uh) +
    (diam_lin * d) + (diam_quad * d2) +
    (diam_lin_uh * event_is_uh * d) +
    (diam_quad_uh * event_is_uh * d2) +
    (hierarchical_model.get('hardness_coefficient', 0.0) * hardness_centered) +
    (hierarchical_model.get('selection_coefficient', 0.0) * selection_centered)
)
# Plus competitor-specific random effect
comp_effect = hierarchical_model.get('competitor_effects', {}).get(comp_key, 0.0)
```

**Recommendation**: Add section explaining baseline sophistication so LLM knows its adjustment role is narrow and focused.

---

#### 4. **QAA Empirical Scaling (150+ Years Validated)**
**System Feature**: Diameter scaling now uses **Queensland Axemen's Association empirical lookup tables** (replaced formula-based scaling in V4.4).

**Current Prompt Status**: ⚠️ **MENTIONED IN DATABASE** but not explained as validation source

Current mention (line 195):
```
WOOD CHARACTERISTICS DATABASE
{wood_data_text}  # Lists species with adjustments
```

**Impact**: LLM doesn't know:
- The 150+ years of institutional knowledge behind species adjustments
- Why certain species have specific adjustment percentages
- That these are competition-validated, not theoretical

**Recommendation**: Add QAA validation context to database introduction.

---

#### 5. **Multi-Event Tournament Context**
**System Feature**: V4.5 introduced multi-event tournaments where each event has independent:
- Wood characteristics
- Competitor selections
- Handicap calculations
- Results tracking

**Current Prompt Status**: ❌ **NO AWARENESS OF EVENT INDEPENDENCE**

**Impact**: When processing multi-event tournaments, LLM doesn't know:
- Tournament weighting applies within-event only (not cross-event)
- Each event is independently handicapped
- Predictions for same competitor can differ dramatically across events (different wood)

**Recommendation**: Add multi-event context parameter (optional, only when in multi-event mode).

---

### Prompt Enhancement Recommendations

#### **Enhancement 1: Add Tournament Context Section** (CRITICAL)
```python
# When tournament_results is provided, add this section after COMPETITOR PROFILE:

TOURNAMENT CONTEXT (CRITICAL):

This competitor has ALREADY COMPETED in this tournament on THIS EXACT WOOD.
Tournament result: {tournament_time:.1f}s (recorded in heat/semi, same block)

IMPORTANCE OF SAME-WOOD DATA:
- Same wood across rounds = MOST ACCURATE predictor possible
- Tournament result from TODAY beats historical data from YEARS AGO
- System applies 97% weight to tournament time, 3% to historical baseline
- Your quality adjustment should be MINIMAL - wood characteristics already proven

BASELINE CALCULATION FOR THIS CASE:
Baseline {baseline:.1f}s = (Tournament {tournament_time:.1f}s × 97%) + (Historical {historical_avg:.1f}s × 3%)

Your task: Apply minor quality adjustment if wood has changed since tournament round.
Expected adjustment: ±1-3% maximum (wood is proven via tournament result).
```

**Rationale**: This is your V4.4 killer feature - LLM must understand why baseline is so heavily weighted toward one recent result.

---

#### **Enhancement 2: Add Adaptive Time-Decay Explanation**
```python
# Add to BASELINE INTERPRETATION section:

TIME-DECAY WEIGHTING (HOW BASELINE WAS CALCULATED):
The baseline uses exponential time-decay weighting with adaptive half-lives:
- Active competitors (frequent recent results): 365-day half-life (recent form emphasized)
- Moderate competitors (standard activity): 730-day half-life (2-year balance)
- Inactive competitors (long gaps): 1095-day half-life (3-year preservation)

For {competitor_name}, system classified as: {activity_level}
Half-life applied: {half_life_days} days

This means:
- Results from THIS SEASON have weight 0.87-1.00 (nearly full weight)
- Results from LAST SEASON have weight ~0.71 (significant but reduced)
- Results from 2-3 YEARS AGO have weight 0.35-0.50 (background only)
- Results from 5+ YEARS AGO have weight <0.10 (almost negligible)

For aging competitors, this ensures predictions reflect CURRENT ability, not historical peak.
The baseline already represents time-weighted reality - your quality adjustment modifies this.
```

**Rationale**: Explains why baseline might seem different from simple historical average.

---

#### **Enhancement 3: Add Baseline V2 Architecture Context**
```python
# Add after BASELINE INTERPRETATION:

BASELINE V2 HYBRID MODEL (WHAT YOU'RE ADJUSTING):

The baseline {baseline:.1f}s is NOT a simple average - it's from a hierarchical regression model:

MODEL COMPONENTS ALREADY IN BASELINE:
✓ Event type effect (SB vs UH scaling)
✓ Diameter curve (polynomial log-space fit)
✓ Wood hardness index (learned from 6 wood properties: Janka, density, crush, shear, MOR, MOE)
✓ Selection bias correction (competitor's typical diameter choice as skill proxy)
✓ Competitor-specific random effect (personalized adjustment with shrinkage)
✓ Time-decay weighting (adaptive half-lives based on activity)
✓ Convergence calibration (finish-time spread minimization for fair handicaps)

MODEL DOES NOT INCLUDE:
✗ Wood quality rating (your job - the ONLY factor not yet in baseline)

YOUR ADJUSTMENT SCOPE:
Since baseline already accounts for species hardness, diameter effects, and competitor ability,
your quality adjustment should be FOCUSED and PRECISE:
- You're fine-tuning for wood CONDITION (soft/hard within the species)
- You're NOT compensating for species hardness (already modeled)
- You're NOT adjusting for diameter (already modeled)
- You're NOT adjusting for competitor skill (already modeled)

Apply quality adjustment to baseline AS-IS, trusting the underlying model.
```

**Rationale**: Prevents LLM from "double-adjusting" for factors already in the model.

---

#### **Enhancement 4: Add QAA Validation Context**
```python
# Modify WOOD CHARACTERISTICS DATABASE section:

WOOD CHARACTERISTICS DATABASE (QAA VALIDATED):

The species adjustments below are derived from the Queensland Axemen's Association (QAA)
empirical handicapping manual, representing 150+ YEARS of Australian woodchopping data.
These are competition-validated, not theoretical estimates.

{wood_data_text}  # Existing species list

QAA VALIDATION:
- Based on thousands of actual competition results
- Separate scaling tables for Hardwood, Medium, Softwood categories
- Proven more reliable than formula-based approaches
- Institutional knowledge from world's longest-running woodchopping association

When species adjustment is listed above, it reflects real-world competition outcomes.
Your quality adjustment modifies CONDITION within the species (softness/hardness variation).
```

**Rationale**: Establishes authority of species adjustments, clarifies LLM's distinct role.

---

### Summary: Prompt 1 Improvements

| Enhancement | Priority | Impact | Complexity |
|-------------|----------|--------|------------|
| Tournament Context | 🔴 CRITICAL | Very High | Low |
| Time-Decay Explanation | 🟠 High | Medium | Low |
| Baseline V2 Architecture | 🟠 High | Medium | Medium |
| QAA Validation | 🟡 Medium | Low | Low |
| Multi-Event Context | 🟢 Low | Low | Low |

**Recommended Action**: Implement Enhancements 1-3 immediately. Enhancement 4 is nice-to-have context. Enhancement 5 only if multi-event prompting issues arise.

---

## Prompt 2: Fairness Assessment Prompt

**Location**: [woodchopping/simulation/fairness.py:176-353](../../woodchopping/simulation/fairness.py#L176-L353)
**Purpose**: Analyzes Monte Carlo simulation results to rate handicap fairness
**Model**: `qwen2.5:32b`
**Token Limit**: 5000 tokens (comprehensive multi-paragraph analysis)

### Current Context Provided ✅

| Context Element | Status | Details |
|-----------------|--------|---------|
| Handicapping principles | ✅ Excellent | Clear equal-probability goal |
| Simulation methodology | ✅ Excellent | 2M races, ±3s absolute variance |
| Statistical significance | ✅ Good | Notes small margin of error |
| Competitor predictions/marks | ✅ Good | Lists all competitors with times |
| Win rate statistics | ✅ Excellent | Actual vs ideal, deviations, spread |
| Finish time analysis | ✅ Good | Average spread, tight finish probabilities |
| Front/back marker performance | ✅ Good | Individual win rates |
| Fairness rating scale | ✅ Excellent | Clear thresholds (Excellent → Unacceptable) |
| Common diagnostic patterns | ✅ Excellent | Front/back marker advantage, etc. |

### Missing Critical Context 🔴

#### 1. **Individual Competitor Time Statistics (NEW V5.0)**
**System Feature**: Monte Carlo simulation now tracks **per-competitor finish time statistics** across all simulations:
- Mean finish time
- Standard deviation
- Min/max range
- Percentiles (p25, p50, p75)
- Consistency rating (Very High → Low based on std_dev thresholds)

**Current Prompt Status**: ❌ **NOT MENTIONED** (added in V5.0 but prompt not updated)

**Impact**: LLM doesn't know to analyze:
- Which competitors have unusually high variance (unpredictable)
- Which competitors show very tight clustering (elite consistency)
- Whether ±3s variance assumption holds per-competitor
- Consistency patterns that might reveal prediction accuracy issues

**Evidence from Code**:
```python
# From fairness.py lines 507-527 (simulate_and_assess_handicaps)
analysis = run_monte_carlo_simulation(competitors_with_marks, num_simulations)
# Returns analysis dict with new field:
# 'competitor_time_stats': {
#     'name': {
#         'mean': float, 'std_dev': float, 'min': float, 'max': float,
#         'p25': float, 'p50': float, 'p75': float,
#         'consistency_rating': str
#     }
# }
```

**Recommendation**: Add competitor statistics section to prompt.

---

#### 2. **Championship vs Handicap Event Mode**
**System Feature**: V5.0 introduced **championship events** where all competitors get Mark 3 (equal start, fastest time wins) vs handicap events (individualized marks for equal finish).

**Current Prompt Status**: ❌ **ASSUMES HANDICAP MODE ALWAYS**

**Impact**: If this prompt is ever used for championship simulator fairness assessment (it's not currently, but architecture allows it), the analysis would be completely wrong. Fairness metrics for championship races are fundamentally different:
- Championship: Win rate spread reflects SKILL disparity (expected, not a problem)
- Handicap: Win rate spread reflects PREDICTION ERROR (problem to fix)

**Recommendation**: Add event type parameter (optional, defaults to handicap).

---

#### 3. **Baseline V2 Hybrid Model Prediction Methods**
**System Feature**: Predictions now use sophisticated Baseline V2 hybrid model (not just simple averages).

**Current Prompt Status**: ⚠️ **ASSUMES GENERIC PREDICTIONS**

Current mention (lines 219-226):
```
COMPETITOR PREDICTIONS AND MARKS:
{competitor_details}
```

**Impact**: When diagnosing prediction issues, LLM doesn't know:
- What level of sophistication went into predictions
- Whether predictions used ML, Baseline V2, or LLM methods
- If tournament weighting was applied (97% same-wood)
- What confidence levels were assigned to predictions

**Recommendation**: Add prediction method metadata to competitor details.

---

#### 4. **Multi-Event Tournament Context**
**System Feature**: Fairness assessment might be for one event within a multi-event tournament.

**Current Prompt Status**: ❌ **NO CONTEXT FOR MULTI-EVENT**

**Impact**: LLM doesn't know:
- This is one event in a larger tournament
- Tournament weighting applies within-event only
- Cross-event win rates aren't relevant for fairness

**Recommendation**: Add tournament context parameter (optional).

---

### Prompt Enhancement Recommendations

#### **Enhancement 1: Add Individual Competitor Statistics Section** (CRITICAL - V5.0 feature)
```python
# Add after SIMULATION RESULTS section:

INDIVIDUAL COMPETITOR TIME STATISTICS (PERFORMANCE CONSISTENCY):

The simulation tracked individual finish times across all {num_simulations:,} races.
This reveals which competitors have PREDICTABLE vs UNPREDICTABLE performance patterns.

PER-COMPETITOR STATISTICS:
{chr(10).join(f"- {name}: mean={stats['mean']:.1f}s, std_dev={stats['std_dev']:.2f}s, range={stats['min']:.1f}s-{stats['max']:.1f}s, consistency={stats['consistency_rating']}"
              for name, stats in competitor_time_stats.items())}

CONSISTENCY RATING THRESHOLDS:
- Very High (std_dev ≤ 2.5s): Elite consistency, highly predictable
- High (std_dev ≤ 3.0s): Normal variance, matches ±3s model assumption
- Moderate (std_dev ≤ 3.5s): Above expected variance
- Low (std_dev > 3.5s): High variability, unpredictable outcomes

VARIANCE MODEL VALIDATION:
The system assumes ±3s absolute performance variation for all competitors.
If a competitor's std_dev significantly exceeds 3.0s, this suggests:
1. Prediction may be inaccurate (wrong baseline time)
2. Competitor has genuinely high performance variability
3. Wood quality or conditions introduce extra uncertainty

CONSISTENCY ANALYSIS TASK:
In your PATTERN DIAGNOSIS section, comment on:
- Are there competitors with unusually high variance (std_dev > 3.5s)?
- Does high variance correlate with prediction confidence (LOW confidence → high variance)?
- Are there competitors with surprisingly tight clustering (std_dev < 2.5s)?
- Does the ±3s model hold across all competitors, or are there outliers?
```

**Rationale**: This is valuable V5.0 data that's being computed but not analyzed by LLM.

---

#### **Enhancement 2: Add Prediction Method Metadata**
```python
# Modify COMPETITOR PREDICTIONS AND MARKS section:

COMPETITOR PREDICTIONS AND MARKS (WITH PREDICTION DETAILS):
{chr(10).join(f"  - {comp['name']}: {comp['predicted_time']:.1f}s predicted +/- Mark {comp['mark']} [Method: {comp.get('method', 'Unknown')}, Confidence: {comp.get('confidence', 'Unknown')}, Tournament Weighted: {comp.get('tournament_weighted', False)}]"
              for comp in sorted(analysis['competitors'], key=lambda x: x['predicted_time'], reverse=True))}

PREDICTION METHOD LEGEND:
- Baseline V2: Hierarchical regression (sophisticated statistical model)
- ML: XGBoost machine learning (trained on historical data)
- LLM: AI-enhanced baseline with quality reasoning

TOURNAMENT WEIGHTED FLAG:
When "Tournament Weighted: True", prediction used 97% same-tournament result + 3% historical.
These are the MOST ACCURATE predictions possible (same wood, recent result).

CONFIDENCE LEVELS:
- VERY HIGH: Tournament weighted or extensive recent data
- HIGH: Good historical data, recent performances
- MEDIUM: Limited data or cross-size/species scaling
- LOW: Sparse data or event baseline fallback

PREDICTION DIAGNOSIS TASK:
When identifying prediction issues in PATTERN DIAGNOSIS:
- Check if biased competitors have LOW confidence (data quality issue)
- Check if biased competitors were tournament weighted (should be very accurate)
- Consider if certain prediction methods systematically over/underpredict
```

**Rationale**: Helps LLM diagnose whether bias is due to bad predictions or bad method selection.

---

#### **Enhancement 3: Add Event Type Context** (Future-proofing)
```python
# Add at beginning after HANDICAPPING PRINCIPLES:

EVENT TYPE: {event_type}  # "handicap" or "championship"

{if event_type == "handicap":
EVENT TYPE: HANDICAP (Individualized Marks)
All competitors receive DIFFERENT marks calculated to equalize finish times.
Win rate spread indicates PREDICTION ACCURACY.
GOAL: All competitors should have equal win probability (~{ideal_win_rate:.1f}% each).

else:
EVENT TYPE: CHAMPIONSHIP (Equal Start)
All competitors receive Mark 3 (start together, fastest time wins).
Win rate spread indicates SKILL DISPARITY (EXPECTED, not an error).
This analysis is for PREDICTIVE ACCURACY, not fairness optimization.
Your FAIRNESS RATING should assess PREDICTION QUALITY, not competitive balance.
}
```

**Rationale**: Prevents confusion if championship mode ever uses this prompt.

---

### Summary: Prompt 2 Improvements

| Enhancement | Priority | Impact | Complexity |
|-------------|----------|--------|------------|
| Competitor Statistics | 🔴 CRITICAL | High | Medium |
| Prediction Method Metadata | 🟠 High | Medium | Low |
| Event Type Context | 🟢 Low | Low | Low |

**Recommended Action**: Implement Enhancement 1 immediately (V5.0 feature not being used). Enhancement 2 improves diagnostic quality. Enhancement 3 is future-proofing only.

---

## Prompt 3: Championship Race Analysis Prompt

**Location**: [woodchopping/simulation/fairness.py:610-669](../../woodchopping/simulation/fairness.py#L610-L669)
**Purpose**: Sports-commentary style race outcome predictions
**Model**: `qwen2.5:32b`
**Token Limit**: 800 tokens (6-section sports commentary)

### Current Context Provided ✅

| Context Element | Status | Details |
|-----------------|--------|---------|
| Win probabilities | ✅ Excellent | Per-competitor from 2M simulations |
| Individual time statistics | ✅ Excellent | Mean, std_dev, range, consistency ratings |
| Close matchups | ✅ Good | Competitors within 2s predicted time |
| Dark horse candidates | ✅ Good | >10% win rate despite not being favorite |
| Consistency outliers | ✅ Good | Very high/very low variance competitors |
| Simulation count | ✅ Good | Notes 2M simulations for statistical confidence |

### Missing Critical Context 🔴

#### 1. **Prediction Method Details**
**System Feature**: Championship simulator uses same prediction engine as handicap system (Baseline V2, ML, LLM).

**Current Prompt Status**: ⚠️ **PREDICTED TIMES PROVIDED** but no method context

**Impact**: LLM doesn't know:
- Which predictions have HIGH vs LOW confidence
- Whether predictions used tournament weighting (highly accurate)
- If predictions required cross-diameter scaling (less certain)
- What data quality underlies the predicted times

**Evidence from Code**:
```python
# From fairness.py line 532-545 (get_championship_race_analysis)
predictions: List[Dict]  # Contains prediction details
# Each prediction has: name, predicted_time, method_used, confidence
```

**Recommendation**: Add prediction confidence context to prompt.

---

#### 2. **Wood Quality Impact on Race Dynamics**
**System Feature**: Wood quality (1-10 scale) affects cutting times, and impact can be UNEVEN across skill levels.

**Current Prompt Status**: ❌ **NO WOOD QUALITY CONTEXT**

**Impact**: LLM can't comment on:
- How soft wood (quality <5) might benefit certain competitors disproportionately
- How hard wood (quality >5) might penalize slower competitors more
- Whether wood quality creates upset potential (soft wood favors dark horses)

**Recommendation**: Add wood characteristics context.

---

#### 3. **Historical Head-to-Head Records**
**System Feature**: System has historical results for all competitors.

**Current Prompt Status**: ❌ **NO HISTORICAL CONTEXT**

**Impact**: Missed opportunity for narrative depth:
- "These two have faced off 5 times, with Smith winning 4"
- "Johnson has never beaten Davis in direct competition"
- "This is a rematch of last year's final"

**Recommendation**: Optional enhancement (requires additional data processing).

---

### Prompt Enhancement Recommendations

#### **Enhancement 1: Add Prediction Confidence Context**
```python
# Add after SIMULATION RESULTS section:

PREDICTION CONFIDENCE ASSESSMENT:

The predicted times above have varying confidence levels based on data quality:

HIGH CONFIDENCE PREDICTIONS (Strong data, reliable):
{chr(10).join(f"- {pred['name']}: {pred['confidence']} confidence via {pred['method_used']}"
              for pred in predictions if pred.get('confidence') in ['VERY HIGH', 'HIGH'])}

LOWER CONFIDENCE PREDICTIONS (Sparse data, more uncertain):
{chr(10).join(f"- {pred['name']}: {pred['confidence']} confidence via {pred['method_used']}"
              for pred in predictions if pred.get('confidence') in ['MEDIUM', 'LOW'])}

CONFIDENCE IMPACT ON RACE ANALYSIS:
- High confidence competitors: Predicted times very reliable, outcomes match predictions
- Low confidence competitors: DARK HORSE potential - prediction may underestimate ability
- Confidence affects upset potential: Low confidence favorite can be beaten by high confidence underdog

ANALYSIS TASK:
In your DARK HORSE / UPSET POTENTIAL section, consider confidence levels:
- Are there low-confidence predictions that could be significantly wrong?
- Could a "dark horse" actually be underestimated due to sparse data?
- Do confidence levels suggest where surprises might occur?
```

**Rationale**: Adds analytical depth to upset predictions.

---

#### **Enhancement 2: Add Wood Quality Impact Context**
```python
# Add at beginning:

WOOD CHARACTERISTICS CONTEXT:

Species: {species_name}
Diameter: {diameter}mm
Quality: {quality}/10 ({"Softer than average - faster cutting" if quality < 5 else "Harder than average - slower cutting" if quality > 5 else "Average hardness"})

QUALITY IMPACT ON RACE DYNAMICS:
{if quality < 5:
Soft wood (quality {quality}) typically benefits ALL competitors, but can create UPSETS:
- Slower competitors gain MORE absolute time than expected (easier cutting)
- Faster competitors gain LESS absolute time (already near optimal)
- Result: Win probabilities may be more EVENLY DISTRIBUTED than predictions suggest
- Dark horse potential is HIGHER in soft wood conditions

else if quality > 5:
Hard wood (quality {quality}) typically penalizes ALL competitors, but reinforces favorites:
- Slower competitors lose MORE absolute time (struggling with hard wood)
- Faster competitors lose LESS absolute time (better technique handles difficulty)
- Result: Win probabilities may be more SKEWED toward favorites than predictions suggest
- Dark horse potential is LOWER in hard wood conditions

else:
Average quality wood (quality 5) - standard conditions, predictions should be accurate.
}

ANALYSIS TASK:
In your RACE DYNAMICS section, comment on how wood quality might affect competitive balance.
```

**Rationale**: Explains environmental factors affecting race outcomes.

---

### Summary: Prompt 3 Improvements

| Enhancement | Priority | Impact | Complexity |
|-------------|----------|--------|------------|
| Prediction Confidence | 🟠 High | Medium | Low |
| Wood Quality Impact | 🟡 Medium | Low | Low |
| Historical Head-to-Head | 🟢 Low | Medium | High |

**Recommended Action**: Implement Enhancement 1 for better upset analysis. Enhancement 2 adds contextual depth. Enhancement 3 is nice-to-have but requires significant data processing.

---

## Cross-Cutting Issues

### Issue 1: Token Limits vs Context Needs
**Problem**: Prompt 1 (Time Prediction) has only 50-token limit but needs to communicate complex context.

**Current State**:
- Prompt is already ~336 lines long
- Adding tournament context would increase further
- 50-token response expected (single number + confidence)

**Recommendation**:
1. **Keep prompt comprehensive** - input tokens don't count against response limit
2. **Increase response token limit to 100-150** - allows for more detailed confidence explanations
3. **Structure prompt with clear sections** - helps LLM parse important vs background context

---

### Issue 2: Prompt Versioning & Maintenance
**Problem**: Prompts are hardcoded in Python files, making it hard to:
- Track changes over time
- A/B test different prompt variants
- Roll back if changes worsen predictions

**Recommendation**:
1. **Create prompt templates directory**: `woodchopping/prompts/`
2. **Use version-tagged files**: `time_prediction_v1.txt`, `time_prediction_v2.txt`
3. **Load prompts at runtime**: `load_prompt_template('time_prediction', version=2)`
4. **Document prompt changes**: `PROMPT_CHANGELOG.md` tracking what changed and why
5. **Enable A/B testing**: Compare v1 vs v2 on same test cases

---

### Issue 3: Prompt Engineering Best Practices
**Current State**: Prompts are well-structured but could benefit from established techniques.

**Recommendations**:
1. **Use XML/JSON tags for structured input**:
   ```xml
   <competitor>
       <name>John Smith</name>
       <baseline_time>45.2</baseline_time>
       <confidence>HIGH</confidence>
       <tournament_result>43.1</tournament_result>
       <tournament_weighted>true</tournament_weighted>
   </competitor>
   ```

2. **Add few-shot examples** for complex reasoning:
   ```
   EXAMPLE 1:
   Input: Baseline 40s, Quality 8 (hard), Historical avg 38s
   Reasoning: Quality 8 is +3 from baseline (quality 5), expect 3×2% = 6% increase
   Output: 1.06 | HIGH | Quality 8 hard wood increases resistance by 6%

   EXAMPLE 2:
   Input: Baseline 50s (tournament weighted 97%), Quality 5
   Reasoning: Tournament result already proven, quality 5 = no adjustment
   Output: 1.00 | VERY HIGH | Tournament result on same wood, no quality adjustment needed
   ```

3. **Use chain-of-thought prompting** for fairness assessment:
   ```
   Let's analyze this step-by-step:
   1. First, what is the win rate spread? {spread:.2f}%
   2. Is this within Excellent (<3%), Very Good (<6%), or Good (<10%) threshold?
   3. Looking at individual win rates, which competitor is most favored?
   4. Is there a systematic pattern (front marker, back marker, middle compression)?
   5. Based on this analysis, what rating and recommendations?
   ```

---

## Implementation Priority Matrix

| Prompt | Enhancement | Priority | Estimated Effort | Expected Impact |
|--------|-------------|----------|------------------|-----------------|
| **Prompt 1** | Tournament Context | 🔴 CRITICAL | 30 min | Very High |
| **Prompt 1** | Time-Decay Explanation | 🟠 High | 20 min | Medium |
| **Prompt 1** | Baseline V2 Architecture | 🟠 High | 45 min | Medium |
| **Prompt 2** | Competitor Statistics | 🔴 CRITICAL | 30 min | High |
| **Prompt 2** | Prediction Metadata | 🟠 High | 20 min | Medium |
| **Prompt 3** | Prediction Confidence | 🟠 High | 15 min | Medium |
| **Prompt 3** | Wood Quality Impact | 🟡 Medium | 20 min | Low |
| **All** | Prompt Versioning System | 🟡 Medium | 2 hours | Medium (long-term) |
| **All** | Few-Shot Examples | 🟢 Low | 1 hour | Medium (quality) |

**Total Critical Work**: ~1 hour
**Total High Priority**: ~1.5 hours
**Total Recommended (Critical + High)**: ~2.5 hours

---

## Testing & Validation Plan

### Phase 1: Baseline Testing (Before Changes)
1. **Capture Current Outputs**: Run 10 test cases (mix of scenarios) and save LLM responses
2. **Record Metrics**:
   - Time prediction accuracy (predicted vs actual if available)
   - Fairness assessment quality (does it catch known issues?)
   - Championship analysis relevance (does it identify actual favorites?)

### Phase 2: Implement Changes
1. **Start with Critical Items**: Tournament context + Competitor statistics
2. **Deploy incrementally**: Update one prompt at a time
3. **Version control**: Tag each prompt version

### Phase 3: A/B Testing
1. **Run same 10 test cases** with new prompts
2. **Compare outputs side-by-side**:
   - Did predictions improve?
   - Is analysis more insightful?
   - Are recommendations more actionable?
3. **Quantitative metrics** (if possible):
   - Prediction MAE before/after
   - Time to identify fairness issues
   - User satisfaction (judge feedback)

### Phase 4: Production Rollout
1. **Deploy to production** if A/B tests show improvement
2. **Monitor for regressions**: Watch for unexpected behavior
3. **Collect judge feedback**: Ask users if analysis quality improved
4. **Iterate**: Refine based on real-world usage

---

## Conclusion

Your STRATHEX system has sophisticated capabilities that **aren't being fully communicated to the LLM**. The most critical gaps are:

### Critical Updates Needed 🔴
1. **Tournament Result Weighting Context** (Prompt 1) - LLM needs to know about 97% same-wood optimization
2. **Individual Competitor Statistics** (Prompt 2) - V5.0 feature not being analyzed

### High-Priority Updates 🟠
3. **Time-Decay & Baseline V2 Explanation** (Prompt 1) - LLM should understand baseline sophistication
4. **Prediction Method Metadata** (Prompt 2) - Helps diagnose prediction quality issues
5. **Prediction Confidence Context** (Prompt 3) - Improves upset/dark horse analysis

### Recommended Next Steps
1. ✅ **Review this audit** (you're here)
2. **Prioritize Critical updates** (implement next)
3. **Test before/after** on known test cases
4. **Deploy incrementally** (one prompt at a time)
5. **Create prompt versioning system** (long-term maintainability)
6. **Document prompt engineering guidelines** (future updates)

### Expected Outcomes
- **Better prediction accuracy**: LLM makes smarter quality adjustments
- **More insightful fairness analysis**: Diagnoses root causes of bias patterns
- **More engaging championship commentary**: Identifies true upset potential
- **System transparency**: Judges better understand AI reasoning

---

**Next Action**: Proceed to Option 2 (Update Prompts) or Option 3 (Create Guidelines) based on your preference.
