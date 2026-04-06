# -*- coding: utf-8 -*-
"""
STRATHEX Explanation System Functions

This module provides interactive explanations of the handicap calculation system
to build trust and understanding among judges, competitors, and officials.

Functions:
    - show_system_overview()
    - show_prediction_methods_explained()
    - show_statistical_glossary()
    - show_technical_deep_dive()
    - explanation_menu()

Author: STRATHEX Project
Purpose: Transparency and education for woodchopping handicapping
"""


# =============================================================================
# MAIN EXPLANATION MENU
# =============================================================================


def explanation_menu():
    """Interactive menu system for learning about handicap calculations."""

    while True:
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 68 + "║")
        print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
        print("║" + "S T R A T H E X".center(68) + "║")
        print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("║" + "Woodchopping Handicap System".center(68) + "║")
        print("║" + "Understanding How It Works".center(68) + "║")
        print("║" + " " * 68 + "║")
        print("╚" + "═" * 68 + "╝")
        print("\n" + "=" * 70)
        print("  STRATHEX HANDICAP SYSTEM - HOW IT WORKS")
        print("=" * 70)
        print("\n  Understanding builds trust. Let's explain how this system")
        print("  calculates fair handicaps for woodchopping competitions.\n")
        print("  1. System Overview - What does this program do?")
        print("  2. Prediction Methods Explained - Manual vs LLM vs ML")
        print("  3. Statistical Glossary - What do all these terms mean?")
        print("  4. Technical Deep Dive - For the technically curious")
        print("  5. Return to Main Menu")
        print("=" * 70)

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            show_system_overview()
        elif choice == "2":
            show_prediction_methods_explained()
        elif choice == "3":
            show_statistical_glossary()
        elif choice == "4":
            show_technical_deep_dive()
        elif choice == "5":
            print("\nReturning to main menu...")
            break
        else:
            print("Invalid choice. Please enter 1-5.")


# =============================================================================
# SYSTEM OVERVIEW
# =============================================================================


def show_system_overview():
    """Explain what the STRATHEX handicap system does and why."""

    print("\n" + "=" * 70)
    print("  SYSTEM OVERVIEW: What Does STRATHEX Do?")
    print("=" * 70)

    print("""
THE HANDICAPPING CHALLENGE

In professional woodchopping, competitors have vastly different skill levels.
A world champion might cut a block in 25 seconds, while a skilled amateur
takes 60 seconds. Without handicapping, the amateur has ZERO chance of winning.

Handicapping solves this by giving faster competitors DELAYED STARTS:
  - Slowest competitor (Mark 3) starts immediately
  - Fastest competitors (higher marks) start later
  - If handicaps are perfect, everyone finishes at the SAME TIME
  - Natural variation (±3 seconds) creates exciting competition

TWO EVENT TYPES: HANDICAP vs CHAMPIONSHIP

STRATHEX supports two competition formats in multi-event tournaments:

HANDICAP EVENTS (What this system is designed for):
  - Each competitor gets an individual handicap mark based on predicted speed
  - Faster competitors start later (higher marks), slower start earlier (lower marks)
  - Goal: Everyone finishes at the same time = exciting finish for spectators
  - Uses AI predictions, historical data, and Monte Carlo validation
  - This is what the rest of this explanation wizard focuses on

CHAMPIONSHIP EVENTS (Traditional racing):
  - ALL competitors receive Mark 3 (simultaneous start)
  - Fastest raw time wins - no predictions needed
  - Traditional "race to the finish" format
  - Faster competitor always wins (no equalizing of skill levels)
  - Common for elite-level competitions where raw speed is the goal

When configuring an event in a multi-event tournament, judges select whether
it's a Handicap or Championship event. Championship events skip all the AI
prediction and handicap calculation steps described below.

THE STRATHEX SOLUTION (For Handicap Events)

This program predicts how fast each competitor will cut a specific block of
wood, then calculates handicap marks so everyone has an EQUAL chance to win.

KEY INNOVATIONS:

1. TRIPLE PREDICTION SYSTEM
   We don't rely on one method - we use THREE different approaches and
   automatically select the most accurate prediction available:

   - BASELINE (Manual): Statistical calculation using historical averages
   - ML MODEL: Machine learning trained on 100+ historical performances
   - LLM: AI-enhanced prediction accounting for wood quality factors

   Selection: Confidence-based scoring (highest-confidence prediction wins).
   VERY HIGH LLM beats LOW Baseline; tournament-day results get a strong bonus.

2. COMPREHENSIVE WOOD FACTORS
   The system accounts for everything that affects cutting speed:
   - Wood species (hardness varies dramatically)
   - Block diameter (more wood = longer cutting time)
   - Wood quality (0-10 scale: soft/rotten vs rock-hard)
   - Competitor's historical performance on similar wood

3. ABSOLUTE VARIANCE MODELING
   CRITICAL INNOVATION: We use ±3 seconds variance for ALL competitors.

   Why? Real-world factors affect everyone equally in ABSOLUTE terms:
   - Wood grain knot costs 2 seconds for novice AND expert
   - Technique wobble affects everyone by similar absolute time
   - Proportional variance (±5% of time) gives unfair advantage to fast choppers

   Tested with 1 million Monte Carlo simulations - absolute variance is FAIRER.

4. FAIRNESS VALIDATION
   Every handicap calculation can be tested with Monte Carlo simulation:
   - Simulates 1 million races with realistic performance variation
   - Measures each competitor's win probability
   - Identifies systematic bias in predictions
   - Rates fairness: Excellent / Very Good / Good / Fair / Poor

THE RESULT

When a judge asks "Why does Joe Smith get Mark 15?" we can show:
  - His historical cutting times (average 28.3s on Standing Block)
  - Adjustment for today's wood (Cottonwood, 380mm, Quality 6)
  - Three independent predictions (Baseline: 29.1s, ML: 28.8s, LLM: 29.3s)
  - Selected prediction: 28.8s (ML - highest confidence)
  - His handicap mark: 15 (calculated from gap to slowest competitor)
  - Monte Carlo validation: System rates "Excellent" (2.1% win rate spread)

This is TRANSPARENT, DEFENSIBLE, and FAIR handicapping.

5. PERSISTENT LEARNING (V6.0 IMPROVEMENT)
   Every competition result is automatically saved to a persistent database.
   After each tournament, results feed back into the prediction engine so that:
   - Predictions improve as more competitions are recorded
   - All past tournament results are available, not just the Excel history
   - The system grows smarter with every event it manages

   This requires no action from judges - it happens automatically on save.
""")

    input("\nPress Enter to continue...")


# =============================================================================
# PREDICTION METHODS EXPLAINED
# =============================================================================


def show_prediction_methods_explained():
    """Explain the three prediction methods with advantages/disadvantages."""

    print("\n" + "=" * 70)
    print("  PREDICTION METHODS: Manual vs LLM vs ML")
    print("=" * 70)

    print("""
The system uses THREE independent prediction methods. Each has strengths
and weaknesses. The program automatically selects the most reliable prediction
available for each competitor.

""")

    print("=" * 70)
    print("  METHOD 1: BASELINE (Manual Statistical Calculation)")
    print("=" * 70)

    print("""
HOW IT WORKS:
1. Calculate TIME-DECAY WEIGHTED average of historical times
   - Recent performances weighted MUCH higher than old results
   - Exponential decay: weight = 0.5^(days_old / 730)
   - Example: 2-year-old result has 50% weight, 10-year-old has 3% weight
   - CRITICAL for aging competitors whose recent ability differs from peak

2. Baseline V2 upgrade (hybrid regression model)
   - Fits a log-time regression using event, diameter curve, wood hardness, and selection bias
   - Adds a competitor-specific effect with shrinkage (more data = more personalized)
   - Uses the same time-decay weighting so recent performance dominates

2. Apply DIAMETER SCALING if needed
   - If historical data is different diameter than today's wood
   - Uses power-law diameter scaling (calibrated from competitor data)
   - Example: Book mark 33s @ 300mm -> 28s @ 275mm (exponent 1.4)
   - Formula: scaled_time = base_time * (target_diameter / base_diameter) ** 1.4

3. Apply WOOD QUALITY adjustment
   - Quality scale: 0 (extremely hard) to 10 (extremely soft)
   - Adjustment: ±2% per quality point from average (5)
   - Quality 8 wood: baseline x 0.94 (6% faster)
   - Quality 2 wood: baseline x 1.06 (6% slower)

4. Confidence assessment based on data quantity and recency

EXAMPLE:
  Competitor: John Smith
  Event: Standing Block
  Historical times:
    - 2018 (7 yrs old, 325mm): 28.5s, 29.1s (weight: 0.06 each, 6%)
    - 2023 (2 yrs old, 325mm): 32.8s, 33.2s (weight: 0.50 each, 50%)
    - 2025 (current, 325mm): 34.1s (weight: 1.00, 100%)

  Time-weighted average: 33.4s (recent times dominate, not old peak!)
  Today's wood: 275mm Aspen (Softwood), Quality 6/10

  Calculation:
    Base (weighted avg): 33.4s @ 300mm equivalent
    Diameter scaling: 33.4s @ 325mm -> 28.0s @ 275mm (power-law exponent 1.4)
    Quality adjustment: 28.0 x 0.98 = 27.4s (quality 6 = slightly softer)
    PREDICTED TIME: 27.4 seconds

ADVANTAGES:
  + ALWAYS AVAILABLE (works even with minimal data)
  + TIME-AWARE (recent form prioritized over old peaks)
  + DATA-DRIVEN (exponent calibrated from actual competition results)
  + EMPIRICAL (based on actual competition data, not formulas)
  + CONSISTENT (same quality adjustment as other methods)
  + TRANSPARENT (lookup tables anyone can verify)
  + RELIABLE (based on actual competitor performance)
  + FAST (instant table lookup)

DISADVANTAGES:
  - SIMPLIFIED (doesn't capture complex interactions)
  - DISCRETE (only standard diameters in tables)
  - LIMITED (only uses event-specific historical data)

WHEN USED:
  - New competitors with 3-5 historical times
  - When ML model has insufficient training data
  - As fallback if LLM prediction fails
  - To validate other prediction methods

""")

    input("Press Enter to continue to LLM explanation...")

    print("\n" + "=" * 70)
    print("  METHOD 2: LLM (AI-Enhanced Prediction)")
    print("=" * 70)

    print("""
HOW IT WORKS:
1. Calculate TIME-DECAY WEIGHTED baseline (same as Baseline method)
   - Recent performances weighted exponentially higher
   - Ensures AI works from competitor's current ability, not old peak

2. System sends detailed prompt to Ollama AI (qwen2.5:7b model)
3. Prompt includes:
   - Time-weighted baseline prediction
   - Competitor's complete historical performance data
   - Wood species characteristics (hardness, grain patterns)
   - Block diameter and quality rating
   - Context about event type and conditions

4. AI reasons about QUALITY-SPECIFIC adjustments
   - How will THIS specific block differ from average?
   - Tight grain? Knots? Moisture? Grain direction?

5. Returns predicted time with reasoning
6. System applies ±2% per quality point adjustment for consistency

EXAMPLE PROMPT TO AI:
  "You are an expert woodchopping handicapper. Predict cutting time for:

   COMPETITOR: John Smith
   Historical Standing Block times: 32.1s, 33.8s, 31.5s, 34.2s (avg: 32.9s)
   Recent trend: Improving (last 3 events faster than average)

   TODAY'S CONDITIONS:
   Species: Cottonwood (Janka hardness 430, specific gravity 0.40)
   Diameter: 380mm
   Quality: 8/10 (firmer than typical Cottonwood - visible tight grain)

   Consider:
   - Cottonwood is soft but this block is firm (Quality 8)
   - Competitor's recent improvement trend
   - 380mm is standard competition size

   Predict cutting time with 1 decimal place. Explain reasoning."

AI RESPONSE EXAMPLE:
  "Predicted time: 31.8 seconds

   Reasoning: John's recent trend shows improving form (last 3 events
   averaged 31.2s vs overall 32.9s). Cottonwood is generally favorable
   for his cutting style, but Quality 8 indicates tighter grain requiring
   more power. The firm grain will slow him slightly (+1.5s) but his
   improving form compensates (-1.6s). Net prediction: 31.8s."

ADVANTAGES:
  + CONTEXTUAL (considers subtle factors like recent form, wood grain)
  + ADAPTIVE (learns patterns from description, not just numbers)
  + REASONING (provides explanation for predictions)
  + NUANCED (handles quality variations better than formulas)

DISADVANTAGES:
  - REQUIRES OLLAMA (must have local AI server running)
  - SLOWER (2-5 seconds per competitor)
  - VARIABLE (same input might give slightly different predictions)
  - OPAQUE (AI reasoning not always fully transparent)
  - REQUIRES DATA (needs good historical information to work well)

WHEN USED:
  - Competitor has 3+ historical times
  - Ollama is running and responsive
  - ML model doesn't have enough training data
  - Wood quality is unusual (very soft or very hard)

RELIABILITY:
  The qwen2.5:7b model was chosen specifically for mathematical reasoning.
  It outperforms GPT-3.5 on numeric prediction tasks while running locally
  (no internet required, no data privacy concerns).

""")

    input("Press Enter to continue to ML explanation...")

    print("\n" + "=" * 70)
    print("  METHOD 3: ML MODEL (XGBoost Machine Learning)")
    print("=" * 70)

    print("""
HOW IT WORKS:
1. System trains TWO separate models (one for SB, one for UH)
2. Training data: ALL historical results in database (100+ events)
   - CRITICAL: Training samples use TIME-DECAY WEIGHTING
   - Recent results have higher influence on model learning
   - Ensures model learns from current competitors, not ancient history

3. Each result is transformed into 23 "features" (EXPANDED V5.0):

   CORE FEATURES (1-10):
   Feature 1: competitor_avg_time_by_event
              - TIME-DECAY WEIGHTED average (recent >> old)
              - Exponential decay: 0.5^(days_old / 730)
              - Ensures feature reflects CURRENT ability
   Feature 2: event_encoded (0 for SB, 1 for UH)
   Feature 3: size_mm (block diameter)

   WOOD PROPERTIES (4-9) - ALL 6 PROPERTIES COMBINED:
   Feature 4: wood_janka_hardness (surface hardness, lbf)
   Feature 5: wood_spec_gravity (density)
   Feature 6: wood_shear_strength (resistance to splitting, PSI) ? BEST SINGLE PREDICTOR
   Feature 7: wood_crush_strength (compression resistance, PSI)
   Feature 8: wood_MOR (Modulus of Rupture - bending strength)
   Feature 9: wood_MOE (Modulus of Elasticity - stiffness)

   COMPETITOR METRICS (10-11):
   Feature 10: competitor_experience (count of past events)
   Feature 11: competitor_trend_slope (improving/declining over time)

   QUALITY & INTERACTIONS (12-16):
   Feature 12: wood_quality (1-10 scale) ? CRITICAL
   Feature 13: diameter_squared (non-linear size effects)
   Feature 14: quality_x_diameter (interaction term)
   Feature 15: quality_x_hardness (interaction term)
   Feature 16: experience_x_size (skilled choppers handle large blocks better)

   CONSISTENCY & RECENCY (17-20):
   Feature 17: competitor_variance (performance consistency)
   Feature 18: competitor_median_diameter (selection bias correction)
   Feature 19: recency_score (momentum vs rust)
   Feature 20: career_phase (rising/peak/declining)

   SEASONAL & EVENT EFFECTS (21-23):
   Feature 21: seasonal_month_sin (cyclical season effects)
   Feature 22: seasonal_month_cos (cyclical season effects)
   Feature 23: event_x_diameter (UH vs SB scaling differences)

   WHY ALL 6 WOOD PROPERTIES?
   Data analysis of 1003 historical results showed:
   - Shear strength alone: r=0.527 correlation with time
   - ALL 6 properties combined: r=0.621 correlation (18.7% improvement!)
   - Multiple linear regression optimally weights each property
   - Combined properties capture complex wood behavior better than any single metric

4. XGBoost algorithm learns patterns:
   - How does diameter affect time? (linear? exponential?)
   - How do ALL 6 wood properties interact with skill levels?
   - Do experienced competitors handle hard wood better?
   - What's the relationship between weighted avg and future performance?
   - How does wood quality affect prediction accuracy?
   - Which competitors are improving vs declining?

5. Model validated with 5-fold cross-validation
6. For new prediction:
   - System feeds 23 features, model outputs base prediction
   - WOOD QUALITY ADJUSTMENT applied: ±2% per quality point
   - Ensures consistency with Baseline and LLM methods

EXAMPLE:
  Competitor: John Smith
  Event: Standing Block

  CORE FEATURES:
    Feature 1 (avg_time): 32.5s (John's SB historical average)
    Feature 2 (event): 0 (Standing Block encoded as 0)
    Feature 3 (size): 380mm

  WOOD PROPERTIES (Cottonwood):
    Feature 4 (janka): 430 lbf
    Feature 5 (spec_gravity): 0.40
    Feature 6 (shear): 920 PSI ?
    Feature 7 (crush): 3500 PSI
    Feature 8 (MOR): 7900 PSI
    Feature 9 (MOE): 1,100,000 PSI

  COMPETITOR METRICS:
    Feature 10 (experience): 8 past SB events
    Feature 11 (trend_slope): +0.2 (improving)

  QUALITY & INTERACTIONS:
    Feature 12 (quality): 5 (average)
    Feature 13 (diameter_squared): 144,400
    Feature 14 (quality_x_diameter): 1900
    (... remaining 9 features calculated automatically ...)

  ML MODEL PREDICTION: 31.4 seconds

  (Model learned that competitors with John's profile typically perform
   0.8s faster than their average on medium-soft wood like Cottonwood)

THE XGBOOST ALGORITHM:
  XGBoost (eXtreme Gradient Boosting) is the gold standard for tabular data.
  It won 17 out of 29 Kaggle competitions in 2015 and is used by:
  - Netflix (recommendation predictions)
  - Airbnb (pricing predictions)
  - Microsoft (Bing search ranking)

  Why? It's EXTREMELY accurate on small-to-medium datasets (our use case).

TRAINING DETAILS:
  - 100 decision trees (each learns from previous tree's mistakes)
  - Max depth 4 (prevents overfitting)
  - Learning rate 0.1 (conservative, stable learning)
  - Cross-validation prevents memorizing training data

ADVANTAGES:
  + MOST ACCURATE (when sufficient training data available)
  + CONSISTENT (same input always gives same prediction)
  + FAST (prediction takes milliseconds)
  + VALIDATED (cross-validation ensures it generalizes well)
  + OBJECTIVE (no human bias in predictions)

DISADVANTAGES:
  - REQUIRES DATA (needs 30+ total events, 15+ per event type)
  - BLACK BOX (harder to explain WHY it predicted a specific time)
  - STATIC (doesn't update until retrained with new data)
  - COLD START (can't predict for brand new competitors)

WHEN USED:
  - Database has 30+ historical results
  - Competitor has at least 1 historical time for this event
  - This is the PREFERRED method when available (most accurate)

CONFIDENCE LEVELS:
  - HIGH confidence: 80+ training records
  - MEDIUM confidence: 50-79 training records
  - LOW confidence: 30-49 training records
  - NOT USED: <30 training records (falls back to LLM or Baseline)

""")

    input("Press Enter to continue to selection priority...")

    print("\n" + "=" * 70)
    print("  PREDICTION METHOD SELECTION PRIORITY")
    print("=" * 70)

    print("""
The system uses INTELLIGENT SELECTION LOGIC that considers data quality:

PRIORITY ORDER (V4.4 - Updated Dec 2025):

    1. BASELINE (SCALED) - IF diameter scaling applied with confidence >= MEDIUM
       -> Physics-based scaling is MORE reliable than ML extrapolation
       -> Example: Historical data from 325mm, predicting for 275mm
       -> Baseline directly scales, ML must extrapolate patterns

    2. ML MODEL - IF >=30 training records AND competitor has event history
       -> Preferred when exact diameter match
       -> Most accurate for "standard" predictions

    3. LLM PREDICTION - IF Ollama running AND >=3 competitor historical times
       -> Good fallback when ML unavailable
       -> Better quality reasoning than baseline alone

    4. BASELINE - Always available as final fallback

WHY THIS MATTERS:

  Diameter scaling example (CRITICAL IMPROVEMENT Dec 2025):

  Competitor with 325mm historical data, predicting for 275mm wood:

  OLD LOGIC (prior to v4.4):
    ML prediction: 33.8s (extrapolating from 325mm pattern - INACCURATE!)
    Result: 9+ second error vs reality

  NEW LOGIC (v4.4+):
    Baseline (scaled): 24.5s (direct physics-based scaling - ACCURATE!)
    Uses: time x (275/325)^1.4
    Result: Matches real-world observations

REAL-WORLD EXAMPLE:

  Heat with 6 competitors calculating Standing Block handicaps:

  - Joe Smith - 15 SB times, all 300mm -> ML PREDICTION (sufficient data, HIGH confidence)
  - Jane Doe - 12 SB times -> ML PREDICTION (sufficient data, HIGH confidence)
  - Bob Wilson - 7 SB times -> ML PREDICTION (meets minimum, LOW confidence [WARN])
  - Amy Chen - 4 SB times -> BASELINE (below recommended, LOW confidence [WARN])
  - New Guy - 2 SB times -> BLOCKED (below absolute minimum N=3)
  - Rookie - 0 SB times -> BLOCKED (no historical data)

DATA REQUIREMENTS (V5.0):
  ABSOLUTE MINIMUM (N=3):
    - System BLOCKS competitor selection if N < 3
    - Cannot calculate handicap with <3 results (statistical minimum)
    - Judge prompted to add historical times before proceeding
    - Prediction error with N < 3: 8-12 seconds (UNACCEPTABLE!)

  RECOMMENDED MINIMUM (N=10):
    - System WARNS if 3 <= N < 10 (displays in selection UI)
    - Competitor CAN be selected but confidence downgraded to LOW
    - Prediction error with N = 3-9: 5-10 seconds (HIGH UNCERTAINTY)
    - Judge informed: "Predictions less reliable, expect wider error"

  SUFFICIENT DATA (N>=10):
    - No warnings, standard confidence calculation applies
    - Prediction error with N >= 10: 2-4 seconds (ACCEPTABLE)
    - This is the target data level for accurate handicapping

WHY THIS PRIORITY?

Testing showed:
  - ML average error: ~2.1 seconds (when data available)
  - LLM average error: ~3.4 seconds
  - Baseline average error: ~4.8 seconds

The system displays ALL THREE predictions (when available) so judges can see:
  - Which method was used for handicap marks
  - How much the predictions agree/disagree
  - Confidence level in the selected prediction

TRANSPARENCY = TRUST

Judges can see the prediction for any competitor and understand exactly:
  1. What data was used (historical times, wood factors)
  2. Which method calculated the handicap mark
  3. Why that method was selected
  4. How confident the system is in the prediction

""")

    input("\nPress Enter to see December 2025 improvements...")

    print("\n" + "=" * 70)
    print("  DECEMBER 2025 SYSTEM IMPROVEMENTS")
    print("=" * 70)

    print("""
VERSION 4.4 - MAJOR ACCURACY UPGRADES

The system received THREE critical improvements that significantly increased
prediction accuracy, especially for aging competitors and cross-diameter
predictions:

----------------------------------------------------------------------
  IMPROVEMENT #1: TIME-DECAY WEIGHTING (Consistent Across All Methods)
----------------------------------------------------------------------

PROBLEM:
  Aging competitors' old peak performances were weighted equally with
  recent results, causing predictions to underestimate current times.

SOLUTION:
  Implemented exponential time-decay weighting: weight = 0.5^(days_old / 730)

  Time-decay weights:
    Current season (0-180 days): 0.87-1.00 weight (87-100% influence)
    Last season (365 days): 0.71 weight (71% influence)
    2 years ago: 0.50 weight (50% influence)
    4 years ago: 0.25 weight (25% influence)
    10 years ago: 0.03 weight (3% influence - essentially ignored)

IMPACT:
  David Moses Jr. example:
    - 2018 peak times (19-22s): Old weighting gave these 33% influence
    - 2023-2025 times (27-29s): Recent performances now dominate
    - Result: Prediction improved by 3.6 seconds (15% more accurate!)

CONSISTENCY:
  Now applied to:
    [OK] Baseline predictions (time-weighted average)
    [OK] LLM predictions (uses time-weighted baseline)
    [OK] ML model training samples (weighted during learning)
    [OK] ML model features (competitor_avg_time_by_event)

----------------------------------------------------------------------
  IMPROVEMENT #2: DIAMETER SCALING (Power-Law Model)
----------------------------------------------------------------------

PROBLEM:
  Competitors with historical data from 325mm blocks being predicted for
  275mm events showed 9+ second errors. ML model tried to extrapolate
  but failed spectacularly.

SOLUTION:
  Power-law diameter scaling calibrated from STRATHEX competitor data.

  How it works:
    - Formula: scaled_time = base_time * (target_diameter / base_diameter) ** 1.4
    - Exponent 1.4 calibrated from actual competition results
    - Applied whenever historical diameter differs from target diameter
    - Example: 27s @ 325mm -> 23s @ 275mm (exponent 1.4)

IMPACT:
  Cody Labahn example (325mm -> 275mm):
    - Historical: 27s average in 325mm blocks
    - OLD: ML predicted 27.4s (ignored diameter difference!)
    - NEW: Power-law scaling: 27s @ 325mm -> 23s @ 275mm
    - Result: 4+ seconds more accurate

INTELLIGENCE:
  Selection logic now PREFERS baseline when diameter scaling applied:
    - Baseline (diameter-scaled) > ML (extrapolating) when diameters differ
    - ML preferred when diameters match (no extrapolation needed)
    - Power-law scaling is reliable, transparent, and invertible

----------------------------------------------------------------------
  IMPROVEMENT #3: WOOD QUALITY CONSISTENCY (Universal Application)
----------------------------------------------------------------------

PROBLEM:
  Only LLM predictions considered wood quality (0-10 scale). Baseline
  and ML ignored it, causing inconsistent handicaps for same competitor.

SOLUTION:
  Standardized quality adjustment across ALL methods: ±2% per quality point

  Quality scale interpretation:
    10 = Extremely soft/rotten -> baseline x 0.90 (10% faster)
    5 = Average hardness -> baseline x 1.00 (no adjustment)
    0 = Extremely hard -> baseline x 1.10 (10% slower)

  Formula: time x (1 + (5 - quality) x 0.02)

IMPACT:
  Quality 8 wood (moderately soft):
    - OLD: Only LLM adjusted for it
    - NEW: All three methods apply -6% adjustment
    - Result: Consistent handicaps regardless of prediction method used

CONSISTENCY:
  Now applied to:
    [OK] Baseline predictions (post-calculation adjustment)
    [OK] ML predictions (post-prediction adjustment)
    [OK] LLM predictions (AI reasoning + standardized adjustment)

----------------------------------------------------------------------
  IMPROVEMENT #4: TOURNAMENT RESULT WEIGHTING (Same-Wood Optimization)
----------------------------------------------------------------------

PROBLEM:
  When competitors advanced from heats to semis to finals, the system
  recalculated handicaps using historical data - completely ignoring the
  fact that they had JUST competed on the SAME WOOD being used in all rounds.

BREAKTHROUGH INSIGHT:
  If a competitor just cut a 275mm Aspen block in 25.3s during the heats,
  and the semi-finals use the SAME 275mm Aspen blocks... that 25.3s is
  the MOST ACCURATE predictor possible!

  Historical data from years ago on different wood? Much less relevant.

SOLUTION:
  Automatic tournament result weighting at 97% for same-tournament times:

  For semis/finals:
    prediction = (heat_time x 0.97) + (historical_baseline x 0.03)

  If competitor has NO historical data:
    prediction = heat_time x 1.00  (use tournament result exclusively)

EXAMPLE:
  Competitor in FINALS after completing heats + semis:

  Heat result: 26.8s (same wood, today)
  Semi result: 27.1s (same wood, today, most recent)
  Historical avg: 24.5s (different wood, years ago)

  OLD SYSTEM (v4.2 and earlier):
    -> Used historical 24.5s baseline
    -> Ignored the 26.8s and 27.1s from TODAY
    -> Mark would be TOO HIGH (unfair disadvantage)

  NEW SYSTEM (v4.4):
    -> Uses most recent tournament time: 27.1s
    -> Weighted: (27.1 x 0.97) + (24.5 x 0.03) = 27.0s
    -> Confidence upgraded from HIGH to VERY HIGH
    -> Mark calculated from 27.0s (much more accurate!)

WHY 97% WEIGHTING (not 100%)?
  - Historical data provides slight stability (prevents single outlier dominance)
  - 97/3 split gives tournament results overwhelming priority
  - If competitor has unusual heat (mishap, equipment issue), historical
    data provides 3% safety net
  - For competitors with NO history, uses 100% tournament time

AUTOMATIC RECALCULATION:
  When you select "Generate Next Round" (Option 8):
    1. System extracts actual times from completed heats/semis
    2. Automatically recalculates ALL handicaps using tournament weighting
    3. Displays: "Recalculating handicaps using tournament results (97% weight)"
    4. Shows which competitors have tournament data applied
    5. New marks reflect most recent performance on SAME wood

IMPACT:
  Multi-round tournaments now have:
    [OK] Maximum accuracy for semis/finals (same-wood optimization)
    [OK] Automatic recalculation (no judge intervention needed)
    [OK] Confidence upgraded to VERY HIGH when tournament data available
    [OK] Fairer handicaps that reflect TODAY'S performance, not history

CONSISTENCY NOTE:
  This feature is ONLY active when:
    - Generating semis from heats, OR
    - Generating finals from semis, OR
    - Generating finals from heats

  Initial heat handicaps still use historical + time-decay + diameter scaling
  (no tournament data exists yet for first round)

----------------------------------------------------------------------
  IMPROVEMENT #5: COMPREHENSIVE WOOD PROPERTIES + DATA QUALITY VALIDATION (V5.0)
----------------------------------------------------------------------

PART A: ALL 6 WOOD PROPERTIES COMBINED

PROBLEM:
  ML model and baseline only used 2 wood properties (Janka hardness + specific
  gravity). Ignored 4 other mechanical properties that significantly affect
  cutting performance.

DATA ANALYSIS:
  Examined 1,003 historical results to determine correlation with time:
    - Janka hardness alone: r=0.414 (moderate correlation)
    - Specific gravity alone: r=0.384 (moderate correlation)
    - Shear strength alone: r=0.527 (BEST single predictor!)
    - Crush strength alone: r=0.447 (good correlation)
    - ALL 6 properties combined: r=0.621 (18.7% IMPROVEMENT!)

WHY ALL 6 PROPERTIES MATTER:
  Wood cutting is a complex mechanical process:
    - Janka hardness: Surface penetration resistance
    - Specific gravity: Overall density
    - Shear strength: Resistance to splitting (CRITICAL for axe work!)
    - Crush strength: Compression resistance at blade contact
    - MOR (Modulus of Rupture): Bending strength (affects grain separation)
    - MOE (Modulus of Elasticity): Stiffness (impacts energy absorption)

SOLUTION:
  1. Event code normalization bug fixed (UH vs uh, SB vs sb)
  2. Expanded ML features from 19 to 23 (added 4 new wood properties)
  3. Updated baseline model to use ALL 6 properties (weighted via regression)
  4. Updated preprocessing to extract all 6 properties from wood database

IMPACT:
  More accurate predictions by capturing wood's complex mechanical behavior:
    - Aspen (soft, low shear): Predicted faster than Janka alone suggested
    - Ironbark (high shear): Predicted slower than density alone suggested
    - Better handling of species with unusual property combinations

PART B: SPARSE DATA WARNINGS & VALIDATION

PROBLEM:
  System showed "VERY HIGH" confidence even for competitors with only 1
  historical result. No validation that minimum data requirements were met.

DATA ANALYSIS:
  Analyzed prediction error vs. result count for 64 competitors:
    - N < 3: 8-12 second prediction error (UNACCEPTABLE!)
    - N = 3-9: 5-10 second prediction error (LOW confidence)
    - N >= 10: 2-4 second prediction error (ACCEPTABLE)

SOLUTION - THREE-TIER VALIDATION SYSTEM:
  1. ABSOLUTE MINIMUM (N=3):
     - Competitors with <3 results are BLOCKED from selection
     - System prevents judge from selecting insufficient data competitors
     - Judge prompted to add historical times to make eligible

  2. RECOMMENDED MINIMUM (N=10):
     - Competitors with 3-9 results show WARNING during selection
     - Judge can proceed but warned: "expect 5-10s error"
     - Confidence rating downgraded to "LOW"

  3. SUFFICIENT DATA (N>=10):
     - No warnings shown
     - Standard confidence calculation applies

WHERE VALIDATION APPEARS:
  [OK] Competitor selection UI (blocks N<3, warns N<10)
  [OK] Multi-event tournament assignment (per-event validation)
  [OK] Championship simulator (blocks N<3 competitors)
  [OK] Heat configuration (displays warnings inline)

PART C: HIGH-VARIANCE DIAMETER FLAGGING

PROBLEM:
  Some diameters showed unpredictable performance (Coefficient of Variation >60%),
  but system didn't warn judges about unreliable predictions.

DATA ANALYSIS:
  Analyzed 1,003 results to identify high-variance diameters:
    - 279mm: CoV = 71% (HIGHEST VARIANCE - wide performance spread)
    - 254mm: CoV = 67%
    - 270mm: CoV = 63%
    - 275mm: CoV = 61%
  Standard diameters (300mm, 250mm, 225mm): CoV < 40% (predictable)

SOLUTION:
  1. High-variance diameter database (279mm, 254mm, 270mm, 275mm flagged)
  2. Warning display during wood selection:
     "WARNING: 279mm diameter has HIGH PERFORMANCE VARIANCE (CoV=71%)
      Predictions may be less reliable - expect wider finish spread"
  3. Sample size check: Warn if <15 historical results for diameter
  4. Recommendation to use standard diameters when possible

WHERE WARNINGS APPEAR:
  [OK] Wood size entry (warns before confirmation)
  [OK] Handicap display (shows warning with marks)
  [OK] Judge can proceed but understands prediction uncertainty

COMBINED IMPACT (V5.0):

  Before:
    ? Missing 4 wood properties (lower prediction accuracy)
    ? Competitor with 1 result shown as "VERY HIGH" confidence
    ? 279mm diameter selected with no warnings
    ? Event code bug causing separate UH/uh baselines

  After:
    [OK] ALL 6 wood properties (18.7% correlation improvement)
    [OK] Competitors with <3 results cannot be selected
    [OK] Competitors with 3-9 results flagged with warnings
    [OK] High-variance diameters automatically detected and flagged
    [OK] Event code normalization ensures consistent predictions
    [OK] Judges fully informed about data quality and prediction reliability

JUDGE BENEFIT:
  System now TRANSPARENTLY communicates prediction reliability:
    - Strong data + standard diameter = High confidence, trust the marks
    - Sparse data + unusual diameter = Low confidence, expect surprises
    - Judges make informed decisions rather than blind trust

----------------------------------------------------------------------

COMBINED IMPACT - Real Competition Example:

  275mm Aspen (Quality 6), Underhand Event:

  Competitor: David Moses Jr.
    - Historical: 19-22s (2018), 27-29s (2023-2025), all from 325mm
    - OLD predictions:
        Baseline: 26.3s (simple mean, no scaling)
        ML: 33.8s (extrapolating incorrectly)
        -> Would mark him TOO HIGH (unfair disadvantage)

    - NEW predictions (v4.4):
        Time-weighted avg: 27.8s (recent form dominates)
        Diameter scaled: 27.8 x (275/325)^1.4 = 23.3s
        Quality adjusted: 23.3 x 0.98 = 22.8s
        -> Matches real-world observations!

  Overall system accuracy improvement: 25-40% for aging competitors with
  cross-diameter predictions.

----------------------------------------------------------------------

VALIDATION & TESTING:

  Test results (Dec 24, 2025):
    - UH (275mm Aspen): 0.8s finish spread [EXCELLENT]
    - SB (300mm EWP): 0.3s finish spread [EXCELLENT]
    - All methods show consistent time-decay weighting
    - Diameter scaling working correctly
    - Quality adjustments uniform across methods

----------------------------------------------------------------------
""")

    input("\nPress Enter to see January 2026 improvements...")

    print("\n" + "=" * 70)
    print("  JANUARY 2026 SYSTEM IMPROVEMENTS - V5.0")
    print("=" * 70)

    print("""
VERSION 5.0 - TOURNAMENT MANAGEMENT & ANALYTICS SUITE

The system received SEVEN new features focused on improving judge workflow,
tournament management, and providing analytical insights for competitors
and officials.

----------------------------------------------------------------------
  FEATURE A1: OFFICIAL SCHEDULE PRINTOUT GENERATOR
----------------------------------------------------------------------

PROBLEM:
  Judges had to manually create printed schedules for competitors and
  spectators. No standardized format, time-consuming, error-prone.

SOLUTION:
  Automated schedule generation with professional formatting:

  Features:
    - Exports formatted TXT file to working directory
    - Shows all rounds with competitor names, marks, stand assignments
    - Includes event details (wood species, diameter, quality, format)
    - Works for both single-event and multi-event tournaments
    - Multi-event: generates COMBINED schedule for entire tournament day

  Menu Location:
    - Single-event: Option 12 "Print Schedule (Export to File)"
    - Multi-event: Option 11 "Print Schedule (Export to File)"

  Format Example:
    ╔════════════════════════════════════════════════════════╗
    ║               TOURNAMENT SCHEDULE                      ║
    ║  Event: 300mm SB                                       ║
    ║  Wood: Douglas Fir, 300mm, Quality 6                   ║
    ╠════════════════════════════════════════════════════════╣
    ║  HEAT 1                                                ║
    ║  Stand 1: John Smith (Mark 15)                         ║
    ║  Stand 2: Jane Doe (Mark 12)                           ║
    ╚════════════════════════════════════════════════════════╝

IMPACT:
  - Saves 15-20 minutes per tournament in schedule preparation
  - Professional appearance for printed materials
  - Eliminates transcription errors
  - Combined day schedules for multi-event tournaments

----------------------------------------------------------------------
  FEATURE A4: REAL-TIME RESULTS ENTRY WITH LIVE STANDINGS
----------------------------------------------------------------------

PROBLEM:
  Judges entered results sequentially but couldn't see live standings or
  advancement status until ALL times were entered. No way to know who was
  "on the bubble" for advancement.

SOLUTION:
  Enhanced results entry workflow showing live standings after EACH time:

  Features:
    - Current placement (1st, 2nd, 3rd, etc.) updates dynamically
    - Advancement status symbols:
        [OK] = Currently advancing (rank <= num_to_advance)
        ? = Eliminated (rank > num_to_advance, all results in)
        ? = TBD (pending more results)
    - Bubble position marked with asterisk (*) on cutoff line
    - Final confirmation before advancing competitors

  Display Example:
    Current Standings - Heat 1
    +-----+-------------------+----------+--------+
    | Pos | Competitor        | Time     | Status |
    +-----+-------------------+----------+--------+
    | 1st | John Smith        | 24.5 sec |   [OK]    |
    | 2nd | Jane Doe          | 26.1 sec |   [OK]    |
    | 3rd | Bob Johnson       | 27.8 sec |   [OK]  * | ? Bubble
    | 4th | Alice Williams    | 29.2 sec |   ?    |
    | 5th | Charlie Brown     |  --  sec |   ?    |
    +-----+-------------------+----------+--------+
    Top 3 advance to next round

IMPACT:
  - Judges can see competitive dynamics unfold in real-time
  - Spectators can follow along as results are entered
  - Eliminates post-entry confusion about who advances
  - Adds excitement to results entry process

----------------------------------------------------------------------
  FEATURE A5: HANDICAP OVERRIDE TRACKER (AUDIT TRAIL)
----------------------------------------------------------------------

PROBLEM:
  When judges manually adjusted handicaps, there was NO RECORD of:
    - What changed (original vs adjusted mark)
    - WHY it changed (reason for adjustment)
    - WHEN it changed (timestamp)

  This made post-event analysis impossible and judge training difficult.

SOLUTION:
  Complete audit trail system for all manual adjustments:

  Captures for each adjustment:
    - Competitor name
    - Event name
    - Original predicted mark
    - Adjusted mark (after judge modification)
    - Reason (required free text from judge)
    - Timestamp (ISO format)
    - Adjustment type (manual vs automatic recalculation)

  Integration Points:
    - Prompts for reason IMMEDIATELY when mark is changed
    - Reason is REQUIRED (system loops until provided)
    - Logs to tournament_state['adjustment_log'] after approval
    - Available for both single-event and multi-event tournaments

  Menu Location:
    - Single-event: Option 7 "View Handicap Adjustment History"
    - Multi-event: Integrated into approval workflow

  Display Example:
    Handicap Adjustment History
    +----------------+----------+----------+---------+------------------+
    | Competitor     | Original | Adjusted | Change  | Reason           |
    +----------------+----------+----------+---------+------------------+
    | John Smith     |    15    |    17    |   +2    | Wood softer than |
    |                |          |          |         | expected         |
    +----------------+----------+----------+---------+------------------+
    | Jane Doe       |    12    |    11    |   -1    | Recent injury,   |
    |                |          |          |         | conservative est |
    +----------------+----------+----------+---------+------------------+

IMPACT:
  - Full accountability for manual adjustments
  - Institutional knowledge preserved (why adjustments were made)
  - Judge training resource (learn from past decisions)
  - Post-event analysis and continuous improvement

----------------------------------------------------------------------
  FEATURE A9 + B2 + B4: ULTIMATE COMPETITOR DASHBOARD
----------------------------------------------------------------------

PROBLEM:
  Judges needed quick access to comprehensive competitor information
  during events, but data was scattered across multiple screens and
  required manual analysis.

SOLUTION:
  Integrated analytics dashboard combining three analytical tools:

  SECTION 1: Career Summary
    - Total competitions across all events
    - Event breakdown (SB vs UH participation)
    - Date range analysis (first/last competition, recency)
    - Data availability assessment

  SECTION 2: Historical Performance Analysis (B2 Integration)
    - Per-event statistics (best time, average, consistency rating)
    - Recent form analysis (last 5 results with trend)
    - Performance trend detection (improving/declining/stable)
    - Consistency ratings:
        VERY CONSISTENT: std_dev <= 2.0s
        CONSISTENT: std_dev <= 3.0s
        MODERATE: std_dev <= 4.0s
        VARIABLE: std_dev > 4.0s

  SECTION 3: Specialization Analysis (B4 Integration)
    - Preferred event, diameter, and species identification
    - Diameter performance breakdown with ratings:
        STRONGEST: >1.0s faster than overall average
        AVERAGE: within ±1.0s of overall average
        WEAKER: >1.0s slower than overall average
    - Species performance breakdown (minimum 3 results required)
    - Outlier detection (z-score ±1.5 threshold)

  Data Handling:
    - Gracefully handles missing dates (only 55% of results have dates)
    - Skips time-series analysis if insufficient dated results
    - Shows "Date information not available" when needed
    - Requires minimum 3 results per category for statistical validity

  Menu Location:
    - ONLY accessible from Personnel Management (Main Menu Option 4)
    - Option 4: "View Competitor Dashboard (Performance Analytics)"
    - NOT in tournament flow (keeps tournament workflow focused)

IMPACT:
  - Judges can make informed decisions about handicaps
  - Identify competitor strengths/weaknesses instantly
  - Detect unusual performances (outliers) that may need investigation
  - Understand performance trends (improving vs declining form)

----------------------------------------------------------------------
  FEATURE B1: PREDICTION ACCURACY TRACKER
----------------------------------------------------------------------

PROBLEM:
  System had no way to track how accurate predictions were vs actual
  results. Judges couldn't validate system performance or identify which
  prediction methods worked best.

SOLUTION:
  On-demand prediction accuracy analysis for completed rounds:

  Error Metrics Calculated:
    - MAE (Mean Absolute Error): Average magnitude of error
    - MPE (Mean Percentage Error): Average percentage error
    - RMSE (Root Mean Square Error): Penalizes large errors more
    - Bias: Positive = underestimating times, Negative = overestimating

  Accuracy Rating Thresholds:
    - EXCELLENT: MAE < 2.0s
    - VERY GOOD: MAE < 3.0s
    - GOOD: MAE < 4.0s
    - FAIR: MAE < 5.0s
    - POOR: MAE >= 5.0s

  Per-Competitor Breakdown:
    - Shows predicted vs actual time for each competitor
    - Identifies largest error (needs attention)
    - Identifies most accurate prediction
    - Percentage error for each prediction

  Per-Method Comparison (if available):
    - Compares Baseline vs ML vs LLM accuracy
    - Identifies which method performed best for this round
    - Helps refine prediction method selection

  Menu Location:
    - Single-event: Option 8 "View Prediction Accuracy Report"
    - ON-DEMAND ONLY (judges must explicitly request)
    - NOT auto-displayed (avoids information overload)

  Storage:
    - Stores accuracy data in tournament_state for trend analysis
    - Includes timestamp for each analysis
    - Can track accuracy improvements over multiple events

IMPACT:
  - Validates system performance objectively
  - Builds trust through transparency
  - Identifies prediction methods that work best
  - Enables continuous improvement based on real data

----------------------------------------------------------------------

COMBINED V5.0 IMPACT - Tournament Management Revolution:

  Before V5.0:
    - Judges manually created schedules (20+ minutes)
    - No live standings during results entry
    - No record of manual adjustments (lost institutional knowledge)
    - Competitor insights required manual data analysis
    - No way to validate prediction accuracy

  After V5.0:
    - Automated schedule generation (< 1 minute)
    - Live standings show competitive dynamics in real-time
    - Complete audit trail for all adjustments
    - Comprehensive competitor analytics at fingertips
    - Objective prediction accuracy tracking

  Workflow Improvements:
    [OK] Schedule export saves 15-20 minutes per tournament
    [OK] Live standings eliminate post-entry confusion
    [OK] Adjustment tracking preserves institutional knowledge
    [OK] Competitor dashboard enables informed handicap decisions
    [OK] Accuracy reports build trust through transparency

  Professional Quality:
    [OK] Printable schedules suitable for official competition materials
    [OK] Real-time standings create spectator engagement
    [OK] Audit trail provides accountability and learning resource
    [OK] Analytics dashboard rivals professional sports systems
    [OK] Accuracy tracking demonstrates system reliability

----------------------------------------------------------------------

  Status: PRODUCTION READY

----------------------------------------------------------------------

For complete technical details, see:
  - docs/TIME_DECAY_CONSISTENCY_UPDATE.md
  - docs/SCALING_IMPROVEMENTS.md
  - docs/SYSTEM_STATUS.md

""")

    input("\nPress Enter to see January 2026 LLM improvements...")

    print("\n" + "=" * 70)
    print("  JANUARY 2026 LLM IMPROVEMENTS - V5.1")
    print("=" * 70)

    print("""
VERSION 5.1 - AI PREDICTION SYSTEM ENHANCEMENTS

The system received SIX critical improvements to the LLM/AI prediction
infrastructure, focusing on accuracy, transparency, and reliability.
These changes make the AI predictions more trustworthy and actionable for judges.

----------------------------------------------------------------------
  IMPROVEMENT L1: LLM CONFIDENCE RATINGS
----------------------------------------------------------------------

PROBLEM:
  The LLM provided quality multipliers but gave no indication of certainty.
  Judges couldn't tell if the AI was confident or guessing. A multiplier of
  1.07 might be highly certain or a wild guess - no way to know.

SOLUTION:
  Enhanced LLM output to include confidence rating with every prediction:

  NEW Response Format:
    <multiplier> | <confidence> | <explanation>
    Example: 1.07 | HIGH | Quality 8 wood increases cutting resistance by 7%

  Confidence Levels:
    - HIGH: Quality clearly defined, well within typical range
    - MEDIUM: Borderline quality or limited historical context
    - LOW: Extreme quality (1-2 or 9-10) or unusual conditions

  Integration with Historical Confidence:
    - LLM confidence DOWNGRADES overall confidence if uncertain
    - Example: Historical data says HIGH, but LLM says LOW -> Overall becomes MEDIUM
    - Prevents false confidence when AI is uncertain about quality adjustment

  OLD SYSTEM (V5.0 and earlier):
    Prediction: 47.3s (Baseline V2, AI calibrated)
    Confidence: HIGH

    ? No indication of AI certainty about quality adjustment
    ? Judge doesn't know if 47.3s is reliable or risky

  NEW SYSTEM (V5.1):
    Prediction: 47.3s (Baseline V2, AI calibrated: Quality 8 increases resistance by 7%)
    LLM Confidence: HIGH -> Overall Confidence: HIGH

    [OK] Judge sees AI is confident about quality assessment
    [OK] Explanation shows reasoning (7% increase for quality 8)
    [OK] Confidence downgrade if AI uncertain

IMPACT:
  - Judges can identify predictions that need manual review
  - LOW confidence triggers closer scrutiny of that competitor's mark
  - Transparency builds trust in AI recommendations
  - Prevents blind acceptance of uncertain AI outputs

----------------------------------------------------------------------
  IMPROVEMENT L2: QUALITY ADJUSTMENT EXPLANATIONS
----------------------------------------------------------------------

PROBLEM:
  LLM returned multipliers (e.g., 1.07) but no reasoning. Judges saw the
  number but not WHY the AI chose it. Made predictions feel like a black box.

SOLUTION:
  LLM now provides one-sentence explanation for every quality adjustment:

  Examples:
    - "Quality 8 wood increases cutting resistance by approximately 7%"
    - "Quality 3 wood reduces cutting time by approximately 5%"
    - "Quality 10 is extremely hard, borderline acceptable wood"
    - "Quality 5 is average, no adjustment needed"

  Display Integration:
    Prediction explanation now shows: "Predicted 47.3s (Baseline V2,
    AI calibrated: Quality 8 wood increases cutting resistance by 7%)"

  OLD SYSTEM (V5.0):
    John Smith: 47.3s (Baseline V2, AI calibrated)

    ? No reasoning visible
    ? Judge must trust blindly

  NEW SYSTEM (V5.1):
    John Smith: 47.3s (Baseline V2, AI calibrated: Quality 8 increases resistance by 7%)

    [OK] Reasoning transparent
    [OK] Judge can verify logic
    [OK] Catches AI errors (if reasoning doesn't match quality rating)

IMPACT:
  - Builds trust through transparency
  - Judges can spot AI reasoning errors
  - Educational - judges learn what quality ratings mean
  - Provides audit trail for post-event review

----------------------------------------------------------------------
  IMPROVEMENT L3: ENHANCED FALLBACK SYSTEMS
----------------------------------------------------------------------

PROBLEM:
  When LLM unavailable (Ollama offline, network issues), system showed
  generic "unavailable" messages. Judges lost critical analysis but got
  no alternative insights.

SOLUTION:
  Robust statistical fallbacks for all LLM features:

  Time Prediction:
    - Falls back to statistical quality adjustment: (quality - 5) x 2%
    - Still provides reasonable prediction, just less nuanced

  Fairness Assessment:
    - Generates statistical assessment based on win rate thresholds
    - Identifies front/back marker bias patterns
    - Provides specific recommendations based on statistics

  Prediction Comparison Analysis:
    - Calculates method agreement statistics automatically
    - Lists high-discrepancy competitors (>20% difference)
    - Provides data quality assessment without AI commentary
    - Shows average differences: ML vs LLM, Baseline vs ML, etc.

  Championship Race Analysis:
    - Shows favorite, matchups, dark horses from pure statistics
    - Includes consistency analysis (std dev, percentiles)
    - Presents as legitimate analysis, not error fallback

  OLD SYSTEM (V5.0):
    "Unable to generate LLM analysis at this time."
    "Error: Connection to Ollama failed"

    ? Judge gets no guidance
    ? Shows technical errors to user

  NEW SYSTEM (V5.1):
    Generates complete statistical analysis including:
    - Method agreement: Average ML vs LLM difference: 2.3 seconds
    - High discrepancy competitors identified
    - Recommendations based on statistics
    - "(Note: Statistical summary - AI analysis unavailable)"

    [OK] Judge still gets actionable insights
    [OK] No error messages shown
    [OK] Graceful degradation

IMPACT:
  - System remains usable even with Ollama offline
  - No confusing error messages for judges
  - Statistical fallbacks are often sufficient for decision-making
  - Judges aren't blocked by technical failures

----------------------------------------------------------------------
  IMPROVEMENT L4: STRUCTURED OUTPUT VALIDATION
----------------------------------------------------------------------

PROBLEM:
  LLM sometimes generated incomplete or malformed responses. System
  displayed partial assessments with missing sections. Judges saw
  truncated analysis and didn't know what was missing.

SOLUTION:
  Validation layer checks all LLM responses for completeness:

  Fairness Assessment Validation:
    Required sections checked:
      - FAIRNESS RATING
      - STATISTICAL ANALYSIS
      - PATTERN DIAGNOSIS
      - PREDICTION ACCURACY
      - RECOMMENDATIONS

    If sections missing, appends warning:
      "[WARN]? AI RESPONSE VALIDATION WARNING:
       The following expected sections were not found:
         - PATTERN DIAGNOSIS
         - RECOMMENDATIONS

       This may indicate the AI response was truncated.
       Consider reviewing raw simulation statistics."

  Rating Validation:
    - Checks for valid rating (EXCELLENT/VERY GOOD/GOOD/FAIR/POOR/UNACCEPTABLE)
    - If invalid, shows expected rating based on statistics
    - Example: "Expected: VERY GOOD based on 4.2% spread"

  Time Prediction Validation:
    - Tries structured format first: "1.07 | HIGH | explanation"
    - Falls back to old format if parsing fails: "1.07"
    - Ensures backward compatibility with older prompts

  OLD SYSTEM (V5.0):
    [Shows incomplete assessment with no indication of problem]

    FAIRNESS RATING: VERY GOOD

    STATISTICAL ANALYSIS: With 4 competitors, ideal win rate is...
    [Response truncated - missing 3 sections]

    ? Judge doesn't know assessment is incomplete

  NEW SYSTEM (V5.1):
    [Same incomplete response BUT with validation warning appended]

    [WARN]? AI RESPONSE VALIDATION WARNING:
    The following expected sections were not found:
      - PATTERN DIAGNOSIS
      - PREDICTION ACCURACY
      - RECOMMENDATIONS

    This may indicate the AI response was truncated.

    [OK] Judge knows to check raw statistics
    [OK] Incomplete analysis flagged explicitly

IMPACT:
  - Judges know when LLM responses are incomplete
  - Prevents relying on partial analysis
  - Highlights need for manual review
  - Catches token limit issues and truncation

----------------------------------------------------------------------
  IMPROVEMENT L5: MODEL CONFIGURATION FIXES
----------------------------------------------------------------------

PROBLEM:
  Three critical bugs in LLM configuration:
    1. Championship analysis referenced non-existent config attribute -> CRASH
    2. Token limits too low for championship analysis -> TRUNCATED RESPONSES
    3. Hardcoded model names inconsistent with config -> CONFUSION

SOLUTION:
  Comprehensive LLM configuration cleanup:

  BUG FIX #1: Added PREDICTION_MODEL to config
    - Championship analysis used llm_config.PREDICTION_MODEL (didn't exist)
    - Added: PREDICTION_MODEL: str = "qwen2.5:32b"
    - Fixed crash in championship race analysis feature

  BUG FIX #2: Token limits updated
    - Added TOKENS_CHAMPIONSHIP_ANALYSIS: int = 800
    - Championship analysis needs 6 sections x ~100 tokens = 600+ tokens
    - Old limit (50 tokens) caused mid-sentence truncation

  BUG FIX #3: Removed hardcoded model strings
    - Changed hardcoded "qwen2.5:7b" -> llm_config.DEFAULT_MODEL
    - All LLM calls now use centralized config
    - Easy to switch models system-wide by changing one config value

  BUG FIX #4: Documentation sync
    - Updated CLAUDE.md to specify qwen2.5:32b (not 7b)
    - Matches actual config values
    - Prevents setup confusion for new users

  BUG FIX #5: Removed wasteful API calls
    - Prediction comparison made test call just to check if Ollama running
    - Removed redundant test - just try the real call and handle failure
    - Reduces latency and API overhead

  OLD SYSTEM (V5.0):
    ? Championship analysis ALWAYS crashed (PREDICTION_MODEL missing)
    ? Responses truncated mid-sentence (50 token limit)
    ? Some code used 7b model, some used 32b (inconsistent)

  NEW SYSTEM (V5.1):
    [OK] Championship analysis works (config attribute exists)
    [OK] Complete responses (800 token limit)
    [OK] All code uses centralized config (consistency)

IMPACT:
  - Championship analysis feature now functional (was broken)
  - No more truncated AI responses
  - Easier to switch between models (7b vs 32b)
  - Reduced latency (no wasteful test calls)

----------------------------------------------------------------------
  IMPROVEMENT L6: MODEL COMPARISON TESTING TOOL
----------------------------------------------------------------------

PROBLEM:
  System can use qwen2.5:7b (faster) or qwen2.5:32b (smarter). No objective
  way to compare which model provides better predictions vs latency tradeoff.

SOLUTION:
  Created comprehensive model comparison testing script:

  Test Suite (test_model_comparison.py):
    - Time Prediction Accuracy: Tests quality multiplier consistency
    - Latency Benchmarking: Measures response time per task type
    - Fairness Assessment Quality: Checks structured output compliance
    - Statistical Analysis: Generates recommendation report

  Usage:
    python test_model_comparison.py

  Output Example:
    TIME PREDICTION ACCURACY:
      qwen2.5:7b: 80.0% accuracy, 2.3s avg latency
      qwen2.5:32b: 100.0% accuracy, 4.1s avg latency
      Winner (Accuracy): qwen2.5:32b
      Winner (Speed): qwen2.5:7b

    FAIRNESS ASSESSMENT QUALITY:
      qwen2.5:7b: Complete=True, 8.2s latency
      qwen2.5:32b: Complete=True, 15.3s latency
      Winner (Quality): TIE

    RECOMMENDATION:
    TROPHY qwen2.5:32b
    The 32B model provides superior accuracy (100% vs 80%) which is
    critical for fair handicapping. Additional latency is acceptable.

  Tests Include:
    - Quality 8 -> should increase time (1.05-1.08 multiplier)
    - Quality 3 -> should decrease time (0.95-0.97 multiplier)
    - Quality 5 -> should not change time (~1.00 multiplier)
    - Extreme cases (quality 1, 10)
    - Structured response parsing compliance

IMPACT:
  - Objective data for model selection decisions
  - Identifies if accuracy difference justifies latency cost
  - Validates that model upgrades improve predictions
  - Provides benchmarks for optimization efforts

----------------------------------------------------------------------

COMBINED V5.1 IMPACT - LLM System Reliability & Transparency:

  Before V5.1:
    ? Championship analysis feature broken (config bug)
    ? LLM predictions felt like black box (no explanations)
    ? No indication of AI confidence level
    ? System unusable when Ollama offline
    ? Incomplete LLM responses shown without warnings
    ? No way to compare different model options

  After V5.1:
    [OK] All LLM features functional and tested
    [OK] Every AI prediction includes reasoning
    [OK] Confidence ratings guide manual review decisions
    [OK] Statistical fallbacks keep system operational
    [OK] Validation warnings flag incomplete responses
    [OK] Model comparison tool enables informed decisions

  Trust & Transparency:
    [OK] Judges see WHY AI made each prediction
    [OK] Confidence levels indicate when to scrutinize
    [OK] Validation catches incomplete/malformed responses
    [OK] Explanations enable learning and verification

  Reliability:
    [OK] Bug fixes eliminate crashes and truncation
    [OK] Fallback systems ensure continuous operation
    [OK] Centralized config prevents inconsistencies
    [OK] Model testing validates accuracy improvements

  Technical Quality:
    [OK] Reduced latency (removed wasteful API calls)
    [OK] Better error handling (graceful degradation)
    [OK] Comprehensive validation (catches edge cases)
    [OK] Documentation sync (setup instructions accurate)

----------------------------------------------------------------------

  Status: PRODUCTION READY

----------------------------------------------------------------------

For testing and validation:
  - test_model_comparison.py (LLM model comparison tool)
  - woodchopping/llm.py (LLM integration layer)
  - config.py (LLMConfig class with all settings)

""")

    input("\nPress Enter to see January 2026 V5.2 improvements...")

    show_v52_improvements()


def show_v52_improvements():
    """Display V5.2 system improvements - Bug fixes and tournament workflow."""
    print("""
======================================================================
  JANUARY 2026 SYSTEM IMPROVEMENTS - V5.2
======================================================================

VERSION 5.2 - TOURNAMENT WORKFLOW STABILITY & BUG FIXES
----------------------------------------------------------------------

This version focuses on stability, fixing critical bugs discovered during
real tournament testing, and improving the user experience for judges.

======================================================================
  IMPROVEMENT #1: POSITION-BASED DRAW LOGIC
======================================================================

PROBLEM:
  When determining which competitors are eligible for a random draw to
  advance to the next round, the system was incorrectly including ALL
  non-advancing competitors instead of only those at the NEXT position.

  Example - 4 heats, top 1 advances from each, need 2 more for finals:

  OLD SYSTEM (V5.1):
    After Heat 1: "Eligible for draw: Bob, Charlie, Dave" (all non-winners)
    After Heat 2: "Eligible for draw: Eve, Frank, Grace" (all non-winners)
    ...
    This was confusing - 3rd and 4th place finishers aren't actually
    eligible until all 2nd place finishers have been drawn.

  NEW SYSTEM (V5.2):
    After Heat 1: "Draw pool (position 2): Bob"
    After Heat 2: "Draw pool (position 2): Eve"
    ...
    Only 2nd place finishers shown - matches AAA rules (Rule 221).

IMPACT:
  - Clearer display of who is actually eligible for draws
  - Prevents confusion about draw eligibility
  - Fills from lowest unfilled position first (2nd place before 3rd)

======================================================================
  IMPROVEMENT #2: OLLAMA CONNECTION CACHING
======================================================================

PROBLEM:
  When Ollama wasn't running, the system would spam error messages:

  "Error: Cannot connect to Ollama..."
  "Error: Cannot connect to Ollama..."
  "Error: Cannot connect to Ollama..."
  (repeated for EVERY competitor)

  This made the output unreadable and confusing for judges.

NEW SYSTEM (V5.2):
  - Connection status is cached for 60 seconds
  - Error message shown ONCE per session, not per competitor
  - Clear boxed notification explains the situation:

    ============================================================
    [WARN] OLLAMA NOT AVAILABLE
    ============================================================
    Cannot connect to Ollama. LLM predictions will be skipped.
    To enable AI predictions, run: ollama serve
    System will continue with Baseline and ML predictions only.
    ============================================================

  - Retry logic with exponential backoff (2 attempts)
  - Graceful fallback to Baseline + ML predictions

IMPACT:
  - Clean, readable output even when Ollama is unavailable
  - System remains fully usable without AI predictions
  - Judges not confused by repeated error messages

======================================================================
  IMPROVEMENT #3: MULTI-EVENT ROUND GENERATION FIX
======================================================================

PROBLEM:
  When advancing from heats to finals in multi-event tournaments,
  the system crashed with:

    KeyError: 'all_competitors_df'

  This was caused by passing incomplete tournament state to the
  round generation function.

CAUSE:
  The multi_event_ui.py was passing:
    {'rounds': event_obj['rounds']}  # Minimal dict - WRONG

  But generate_next_round() needs:
    - all_competitors_df (for filtering advancers)
    - wood_species, wood_diameter, wood_quality, event_code
      (for recalculating handicaps with tournament weighting)

FIX:
  Now passes the complete event_obj which has all required fields.

IMPACT:
  - Multi-event tournaments now work correctly through all rounds
  - Heats → Semis → Finals progression works
  - Tournament result weighting (97%) applied correctly

======================================================================
  IMPROVEMENT #4: TOURNAMENT PAYOUT CONFIGURATION
======================================================================

PROBLEM:
  The Finance menu option "Configure Event Payouts" showed:
    "Payout configuration feature coming soon"

  Judges couldn't configure payouts for events after creation.

NEW SYSTEM (V5.2):
  Full payout configuration menu:
  - View current payout status for all events at a glance
  - Select any event to configure/modify payouts
  - Copy payout configuration from one event to multiple others
    (useful when many events have identical purses)
  - Remove payout configurations

IMPACT:
  - Judges can configure payouts at any time, not just during creation
  - Batch copy saves time for multi-event tournaments
  - Complete finance workflow now functional

======================================================================
  IMPROVEMENT #5: JSON SERIALIZATION FIX
======================================================================

PROBLEM:
  Tournament state saving failed with:
    "Object of type DataFrame is not JSON serializable"

  This was caused by a new V5.1 field (competitor_roster_df) that
  wasn't being converted before JSON serialization.

FIX:
  - Save function now converts competitor_roster_df to dict records
  - Load function reconstructs it back to DataFrame

IMPACT:
  - Tournament state saves correctly
  - Auto-save works without errors
  - Tournament recovery from saved state works

----------------------------------------------------------------------

COMBINED V5.2 IMPACT - Stability & Reliability:

  Before V5.2:
    [X] Confusing draw eligibility display
    [X] Error spam when Ollama unavailable
    [X] Crash when advancing multi-event rounds
    [X] Payout configuration incomplete
    [X] Tournament save failures

  After V5.2:
    [OK] Clear position-based draw pool display
    [OK] Single, clear Ollama status message
    [OK] Smooth multi-event tournament progression
    [OK] Complete payout configuration workflow
    [OK] Reliable tournament state persistence

----------------------------------------------------------------------

  Status: PRODUCTION READY

----------------------------------------------------------------------

""")

    print("""
======================================================================
  MARCH 2026 SYSTEM IMPROVEMENTS - V6.0
======================================================================

V6.0 is an internal engineering upgrade. The prediction methodology,
AAA rules compliance, and fairness model are UNCHANGED. Judges will
notice no difference in results. The improvements are under the hood:

======================================================================
  IMPROVEMENT #1: PERSISTENT LEARNING DATABASE
======================================================================

Previously: Results were stored only in woodchopping.xlsx. Each fresh
installation started with no memory of past competitions.

V6.0: Every competition result is automatically saved to a persistent
database (SQLite at ~/.strathmark/results.db). Results accumulate across
ALL competitions — not just the current Excel file.

What this means for judges:
  - Predictions improve automatically as more competitions are recorded
  - A competitor who has competed at 10 tournaments has all 10 remembered
  - The system gets smarter every event, without any manual action

How it works:
  - On program startup: historical Excel results are migrated to the database
  - After every results save: times are automatically written to both Excel
    AND the persistent database
  - Both data sources are used when calculating handicaps

======================================================================
  IMPROVEMENT #2: SMARTER PREDICTION SELECTION
======================================================================

Previously: Fixed priority order (ML > LLM > Baseline cascade).

V6.0: Confidence-based scoring. Each prediction is scored by how much
error it's likely to have, then the lowest-error prediction is chosen.

What this means for judges:
  - A VERY HIGH confidence AI prediction now beats a LOW confidence
    statistical baseline, even if the baseline would previously have won
  - Tournament-day results get a strong scoring bonus (they should -
    same wood, same day is the best predictor available)
  - The 3-column display (Baseline / ML / LLM) is unchanged - judges
    still see all three predictions and which was selected

======================================================================
  IMPROVEMENT #3: EXTERNAL ENGINE (STRATHMARK)
======================================================================

Previously: Calculation logic was embedded directly in STRATHEX.

V6.0: Calculation logic lives in a separate installable library called
STRATHMARK. STRATHEX calls STRATHMARK for all calculations.

What this means for judges: Nothing changes. Same handicaps, same
displays, same workflow. This is a developer improvement that makes
the calculation engine independently testable and reusable.

Future benefit: STRATHMARK can power mobile apps, web interfaces, or
other competition tools while sharing the same proven calculation engine.

----------------------------------------------------------------------

COMBINED V6.0 IMPACT:

  Before V6.0:
    [X] Predictions start from scratch at each installation
    [X] Fixed ML > LLM > Baseline cascade (regardless of confidence)
    [X] No HTTP API for future integrations

  After V6.0:
    [OK] Persistent learning - predictions improve over all competitions
    [OK] Confidence-based selection - best prediction always chosen
    [OK] HTTP REST API available for future web/mobile consumers
    [OK] All 28 STRATHMARK engine tests passing

----------------------------------------------------------------------

  Status: PRODUCTION READY

----------------------------------------------------------------------

""")

    input("\nPress Enter to return to menu...")


# =============================================================================
# STATISTICAL GLOSSARY
# =============================================================================


def show_statistical_glossary():
    """Comprehensive glossary of all statistical terms used in the program."""

    terms = [
        {
            "term": "AVERAGE (MEAN)",
            "definition": "The sum of all values divided by the count of values.",
            "example": "If John cut blocks in 30s, 32s, 28s, 31s, and 29s, his average is (30+32+28+31+29)÷5 = 30.0 seconds.",
            "relevance": "Used to calculate a competitor's typical performance. The baseline prediction starts with their historical average.",
            "where_seen": "Handicap calculation screen, prediction methods display",
        },
        {
            "term": "STANDARD DEVIATION (STD DEV)",
            "definition": "Measures how spread out values are from the average. Low = consistent, high = variable.",
            "example": "Competitor A: times of 30s, 30s, 31s (std dev ~0.5s - very consistent)\nCompetitor B: times of 25s, 35s, 30s (std dev ~4.1s - inconsistent)",
            "relevance": "Shows performance consistency. Consistent competitors are more predictable. We use ±3 second standard deviation in Monte Carlo simulations.",
            "where_seen": "Monte Carlo simulation results, statistical analysis section",
        },
        {
            "term": "IQR (INTERQUARTILE RANGE)",
            "definition": "The range containing the middle 50% of data values. Calculated as Q3 - Q1 (75th percentile minus 25th percentile).",
            "example": "Times: 25, 27, 28, 30, 31, 33, 45 seconds\nQ1 (25th %ile) = 27s, Q3 (75th %ile) = 33s\nIQR = 33 - 27 = 6 seconds",
            "relevance": "Used for robust outlier detection. IQR is not affected by extreme values, unlike standard deviation.",
            "where_seen": "Data validation process (background), you won't see this directly",
        },
        {
            "term": "3xIQR (OUTLIER DETECTION)",
            "definition": "A value is an extreme outlier if it's more than 3xIQR away from the quartiles. This is a very conservative threshold.",
            "example": "If IQR = 6s, outlier threshold is 18s from quartiles.\nTimes: 28, 29, 30, 31, 85s ? 85s is flagged and removed",
            "relevance": "Removes data entry errors and invalid results (like a competitor who stopped mid-cut). Only extreme outliers are removed to preserve real performance variation.",
            "where_seen": "Data validation warnings when loading historical results",
        },
        {
            "term": "OUTLIER",
            "definition": "A data point that is extremely different from others. Could be error or genuine exceptional performance.",
            "example": "If most times are 28-35s, a time of 95s is probably an error (competitor fell, axe broke, etc.)",
            "relevance": "Outliers distort averages and predictions. System removes only EXTREME outliers (3xIQR method) to prevent errors while keeping genuine performances.",
            "where_seen": "Data validation report shows how many outliers were detected and removed",
        },
        {
            "term": "BASELINE TIME / BASELINE PREDICTION",
            "definition": "The manual statistical prediction method using historical averages + adjustment factors.",
            "example": "Baseline for Joe on Cottonwood 380mm: His avg (32s) x species factor (0.95) x quality factor (1.08) = 32.8s",
            "relevance": 'This is the "fallback" prediction method that always works. Simple, transparent, reliable.',
            "where_seen": 'Handicap display shows "Baseline: 32.8s" alongside ML and LLM predictions',
        },
        {
            "term": "ADJUSTMENT FACTOR",
            "definition": "A multiplier applied to base time to account for wood characteristics. Usually ranges from 0.85 to 1.20.",
            "example": "Soft wood species: 0.90 factor (10% faster)\nHard wood species: 1.10 factor (10% slower)\nQuality 9/10 (very hard): +8% adjustment",
            "relevance": "Adjusts predictions for today's specific wood. Same competitor will have different predictions on pine vs oak.",
            "where_seen": "Visible in baseline prediction explanations and detailed calculation breakdowns",
        },
        {
            "term": "HANDICAP MARK",
            "definition": "The number called for a competitor that determines their start delay. Mark 3 = start immediately, Mark 20 = wait 17 seconds.",
            "example": 'Front marker (slowest): Mark 3 (starts at "Mark 3!")\nBack marker (fastest): Mark 18 (waits 15 seconds, starts at "Mark 18!")',
            "relevance": "THIS IS THE MAIN OUTPUT. The handicap mark equalizes competition by giving faster competitors delayed starts.",
            "where_seen": "Main handicap display, heat assignments, announcer calls",
        },
        {
            "term": "GAP",
            "definition": "The predicted time difference between a competitor and the slowest competitor. Used to calculate handicap marks.",
            "example": "Slowest competitor: predicted 55.0s\nJoe Smith: predicted 42.0s\nGap = 55.0 - 42.0 = 13.0s -> Mark 16 (3 + 13 rounded up)",
            "relevance": "Larger gap = higher mark = longer delay. The gap directly converts predicted time into start delay.",
            "where_seen": "Calculation process (background), visible in detailed handicap explanations",
        },
        {
            "term": "FRONT MARKER",
            "definition": "The slowest predicted competitor who receives Mark 3 (starts first). Acts as the baseline for all other marks.",
            "example": 'If Sue is predicted slowest at 58.2s, she gets Mark 3 and starts immediately when "Mark 3!" is called.',
            "relevance": "Front marker has NO delay. All other competitors' delays are calculated relative to them.",
            "where_seen": "Handicap results display, Monte Carlo simulation analysis",
        },
        {
            "term": "BACK MARKER",
            "definition": "The fastest predicted competitor who receives the highest mark (starts last with longest delay).",
            "example": "If John is predicted fastest at 28.5s and slowest is 55.0s, gap is 26.5s -> Mark 30 (3 + 27). He waits 27 seconds.",
            "relevance": "Back marker has the LONGEST delay. In a perfect handicap system, they should finish at the same time as front marker.",
            "where_seen": "Handicap results display, Monte Carlo simulation analysis",
        },
        {
            "term": "MONTE CARLO SIMULATION",
            "definition": "A method that runs thousands/millions of virtual races with random performance variation to test handicap fairness.",
            "example": "System runs 1,000,000 simulated races:\n- Each race, competitors vary ±3s from predicted time\n- Count who wins each race\n- Calculate win probability for each competitor",
            "relevance": "Validates that handicaps are FAIR. If one competitor wins 40% of simulations while others win 5%, the handicaps are biased.",
            "where_seen": "Optional fairness analysis after calculating handicaps (Menu Option 5)",
        },
        {
            "term": "WIN PROBABILITY / WIN RATE",
            "definition": "The percentage of simulated races won by each competitor. Ideally, all competitors should have equal win probability.",
            "example": "Heat with 5 competitors:\nIdeal: 20% win rate each (5 competitors = 100%÷5)\nActual: Joe 23%, Sue 21%, Bob 19%, Amy 22%, Dan 15%\nDan is disadvantaged (15% vs 20% ideal)",
            "relevance": "Measures handicap fairness. Spread <3% = Excellent, <6% = Very Good, <10% = Good, >16% = Poor.",
            "where_seen": "Monte Carlo simulation results, displayed as bar charts and percentages",
        },
        {
            "term": "WIN RATE SPREAD",
            "definition": "The difference between highest and lowest win rates. Lower spread = fairer handicaps.",
            "example": 'Highest win rate: 22.5%\nLowest win rate: 18.7%\nSpread = 22.5 - 18.7 = 3.8% (rates as "Very Good")',
            "relevance": "PRIMARY FAIRNESS METRIC. Spread <3% means handicaps are nearly perfect. >10% means predictions have systematic bias.",
            "where_seen": "Monte Carlo simulation summary, AI fairness assessment",
        },
        {
            "term": "CONFIDENCE LEVEL",
            "definition": "How much historical data supports a prediction. More data = higher confidence = more reliable prediction.",
            "example": "HIGH: Competitor has 12 past events, ML trained on 95 records\nMEDIUM: Competitor has 4 past events, ML trained on 55 records\nLOW: Competitor has 3 past events, ML trained on 35 records",
            "relevance": "Tells judges how much to trust a prediction. LOW confidence predictions might be adjusted for safety.",
            "where_seen": "Prediction methods summary shows ML confidence level (HIGH/MEDIUM/LOW)",
        },
        {
            "term": "LLM (LARGE LANGUAGE MODEL)",
            "definition": "An AI system trained on massive text data that can understand context and make intelligent predictions. Like ChatGPT but specialized.",
            "example": "qwen2.5:7b model (7 billion parameters) running on Ollama. Optimized for mathematical reasoning tasks.",
            "relevance": "LLM prediction method uses AI to consider subtle factors like wood quality, recent form, and species characteristics that formulas might miss.",
            "where_seen": 'Prediction methods display shows "LLM Model: 31.2s" when LLM prediction is available',
        },
        {
            "term": "ML (MACHINE LEARNING)",
            "definition": "Computer algorithms that learn patterns from historical data and use those patterns to make predictions on new data.",
            "example": 'ML model learns: "Competitors 2s faster than average on soft wood" or "380mm blocks take 1.2x longer than 320mm blocks"',
            "relevance": "ML prediction method is the MOST ACCURATE when enough training data exists. Learns complex patterns humans might miss.",
            "where_seen": 'Prediction methods display shows "ML Model: 30.8s" when ML prediction is used',
        },
        {
            "term": "TRAINING DATA",
            "definition": "Historical competition results used to teach the ML model patterns. More training data = better predictions.",
            "example": "Database with 127 historical results:\n- 68 Standing Block times\n- 59 Underhand times\n- Spanning 15 different competitors\n- 8 different wood species",
            "relevance": "ML model needs minimum 30 total records (15 per event type) to make reliable predictions. Quality matters more than quantity.",
            "where_seen": 'Prediction methods summary shows "ML Model: XGBoost trained on 127 records"',
        },
        {
            "term": "XGBOOST",
            "definition": "eXtreme Gradient Boosting - a specific ML algorithm that's highly accurate for prediction tasks with structured data.",
            "example": "XGBoost won 17 of 29 Kaggle competitions in 2015. Used by Microsoft, Netflix, Airbnb for predictions.",
            "relevance": "We chose XGBoost because it's the gold standard for small-to-medium tabular datasets (our exact use case).",
            "where_seen": "Technical documentation, prediction methods explanation",
        },
        {
            "term": "CROSS-VALIDATION (CV)",
            "definition": "A technique to test ML model accuracy by training on part of data and testing on another part. Prevents overfitting.",
            "example": "5-fold CV: Split data into 5 parts, train on 4, test on 1. Repeat 5 times. Average the results.",
            "relevance": "Ensures ML model works on NEW data, not just memorizing training data. Validates prediction reliability.",
            "where_seen": "Background process during ML training (not directly visible to user)",
        },
        {
            "term": "FEATURE ENGINEERING",
            "definition": 'Converting raw data into "features" (numerical inputs) that ML models can learn from.',
            "example": 'Raw data: "Standing Block, Cottonwood, 380mm"\nFeatures: event=0, janka=430, spec_gravity=0.40, size=380',
            "relevance": "ML models need numbers, not text. Feature engineering transforms wood characteristics into learnable patterns.",
            "where_seen": "Background process (not directly visible), mentioned in technical documentation",
        },
        {
            "term": "PREDICTION",
            "definition": "An estimated cutting time for a competitor on a specific block of wood, calculated before the competition.",
            "example": "System predicts Joe will cut this Cottonwood block in 31.4 seconds based on his history and wood characteristics.",
            "relevance": "Predictions are converted into handicap marks. Accurate predictions = fair competition.",
            "where_seen": "Main handicap display shows predicted times alongside marks for each competitor",
        },
        {
            "term": "QUALITY RATING (0-10 SCALE)",
            "definition": "Judge's assessment of wood firmness/difficulty. 0=rotten/soft, 5=average, 10=exceptionally hard.",
            "example": "Quality 3: Soft Cottonwood with loose grain (cuts fast)\nQuality 7: Firm Cottonwood with tight grain (cuts slower)\nQuality 10: Rock-hard oak, nearly impossible",
            "relevance": "CRITICAL INPUT. Same species varies dramatically. Quality 3 vs Quality 9 can change times by 20%+.",
            "where_seen": "Wood characteristics input (Menu Option 1), displayed in all handicap calculations",
        },
        {
            "term": "SPECIES HARDNESS / JANKA HARDNESS",
            "definition": "Standard measure of wood hardness (pounds of force to embed steel ball halfway). Higher = harder to cut.",
            "example": "Cottonwood: 430 lbf (soft)\nDouglas Fir: 710 lbf (medium)\nWhite Oak: 1360 lbf (very hard)",
            "relevance": "Different species cut at vastly different speeds. ML model uses Janka hardness as a feature for predictions.",
            "where_seen": "Wood species data (background), technical deep dive explanations",
        },
        {
            "term": "SPECIFIC GRAVITY",
            "definition": "Wood density relative to water. Higher = denser = more material to cut through.",
            "example": "Cottonwood: 0.40 (light, airy)\nPine: 0.55 (medium density)  \nOak: 0.75 (dense, heavy)",
            "relevance": "Denser wood takes longer to cut (more material). ML model uses specific gravity to refine predictions.",
            "where_seen": "Wood species data (background), technical deep dive explanations",
        },
        {
            "term": "ABSOLUTE VARIANCE (±3 SECONDS)",
            "definition": "Every competitor varies by the SAME number of seconds (±3s), not a percentage. Critical for fairness.",
            "example": "Fast chopper (30s predicted): actual time between 27-33s\nSlow chopper (60s predicted): actual time between 57-63s\nBOTH vary by ±3s absolute",
            "relevance": "MAJOR INNOVATION. Proportional variance (±5%) gives unfair advantage to fast choppers. Real factors (grain knots, fatigue) affect everyone equally in seconds, not percentages.",
            "where_seen": "Monte Carlo simulation methodology, system overview documentation",
        },
        {
            "term": "PROPORTIONAL VARIANCE",
            "definition": "Variation as a percentage of predicted time (e.g., ±5%). REJECTED by this system as unfair.",
            "example": "With ±5% variance:\nFast chopper (30s): varies 27-33s (±3s range)\nSlow chopper (60s): varies 54-66s (±6s range)\nSlow chopper gets DOUBLE the variation!",
            "relevance": "Proportional variance creates bias. Testing showed 31% win rate spread vs 6.7% with absolute variance. This is why we use absolute.",
            "where_seen": "System documentation, mentioned in technical explanations of fairness",
        },
    ]

    print("\n" + "=" * 70)
    print("  STATISTICAL GLOSSARY")
    print("=" * 70)
    print("\n  Complete reference for every statistical term used in STRATHEX.\n")

    for i, entry in enumerate(terms, 1):
        print("\n" + "=" * 70)
        print(f"  TERM {i} of {len(terms)}: {entry['term']}")
        print("=" * 70)

        print("\nDEFINITION:")
        print(f"  {entry['definition']}")

        print("\nEXAMPLE:")
        for line in entry["example"].split("\n"):
            print(f"  {line}")

        print("\nWHY IT MATTERS FOR WOODCHOPPING:")
        print(f"  {entry['relevance']}")

        print("\nWHERE YOU'LL SEE IT:")
        print(f"  {entry['where_seen']}")

        if i < len(terms):
            cont = input("\nPress Enter for next term (or 'q' to return to menu): ").strip().lower()
            if cont == "q":
                break

    print("\n" + "=" * 70)
    print("  End of Statistical Glossary")
    print("=" * 70)
    input("\nPress Enter to return to menu...")


# =============================================================================
# TECHNICAL DEEP DIVE
# =============================================================================


def show_technical_deep_dive():
    """Detailed technical explanation with wizard ASCII art."""

    print("\n")
    print("""
      ╔════════════════════════════════════════════════════════════╗
      ║     ⚠️  DANGER: MAXIMUM NERDERY AHEAD! ⚠️                   ║
      ║                                                            ║
      ║  Congratulations! You've found the secret developer        ║
      ║  backdoor where we keep the REALLY nerdy stuff.            ║
      ║                                                            ║
      ║  If you were hoping for a quick explanation, turn back     ║
      ║  now. If you want to know EXACTLY how the sausage is       ║
      ║  made, including all the weird edge cases and sketchy      ║
      ║  assumptions we hope nobody asks about... buckle up.       ║
      ║                                                            ║
      ║  The Wizard is about to spill ALL the algorithmic tea.     ║
      ║                                                            ║
      ║  🧙 "I solemnly swear I will over-explain everything."     ║
      ║                                                            ║
      ╚════════════════════════════════════════════════════════════╝



            ____
            .'* *.'
            __/_*_*(_
            / _______ \
            _\\_)/___\\(_/_
            / _((\\- -/))_ \
            \\ \\())(-)(()/ /
            ' \\(((()))/ '
            / ' \\)).))/ ' \
            / _ \\ - | - /_  \
            (   ( .;''';. .'  )
            _\"__ /    )\\ __"/_
            \\/  \\   ' /  \\/
            .'  '...' ' )
            / /  |  \\ \
            / .   .   . \
            /   .     .   \
            /   /   |   \\   \
            .'   /    b    '.  '.
            _.-'    /     Bb     '-. '-._
            _.-'       |      BBb       '-.  '-.
            (___________\\____.dBBBb.________)____)




      ════════════════════════════════════════════════════════════════
    """)

    input("\n🧙 Press Enter to descend into the technical rabbit hole...\n")

    print("\n" + "=" * 70)
    print("  🔮 THE WIZARD'S GRIMOIRE OF QUESTIONABLE STATISTICAL DECISIONS 🔮")
    print("=" * 70)

    print("""

🧙 "Ah, a fellow nerd! Excellent! Let me tell you EXACTLY how this works,
including the parts we don't usually mention in polite company.

Look, I'm not gonna lie - predicting the future is HARD. We're basically
trying to guess how fast someone will swing an axe at a piece of wood based
on how fast they swung axes at DIFFERENT pieces of wood in the past.

It's like trying to predict your Uber rating based on your bowling scores.
Will it work? ...Maybe? Let's find out together!"

----------------------------------------------------------------------
""")

    input("Press Enter to continue...\n")

    print("=" * 70)
    print("  SPELL #1: BASELINE PREDICTION ALGORITHM")
    print("=" * 70)

    print("""
? "The Baseline method is my 'Apprentice-Level' spell - simple but reliable.
Here's EXACTLY how it works, step by step:"

ALGORITHM PSEUDOCODE:
---------------------
1. competitor_history = GET all historical times for this competitor + event
2. IF len(competitor_history) < 3:
       RETURN "Insufficient data - need minimum 3 historical times"
3. base_time = AVERAGE(competitor_history)
4. species_factor = LOOKUP species in wood database
5. quality_adjustment = CALCULATE from quality rating (0-10 scale)
6. diameter_adjustment = CALCULATE from block diameter
7. confidence_penalty = CALCULATE from amount of historical data
8. predicted_time = base_time x species_factor x quality_adjustment
                    x diameter_adjustment + confidence_penalty
9. RETURN predicted_time

ACTUAL CODE (simplified from FunctionsLibrary.py):
--------------------------------------------------

    def predict_baseline(competitor_name, event, species, diameter, quality):
        # Get historical times for this competitor + event type
        historical_times = results_df[
            (results_df['competitor_name'] == competitor_name) &
            (results_df['event'] == event)
        ]['raw_time'].values

        if len(historical_times) < 3:
            return None  # Insufficient data

        # Calculate base time (historical average)
        base_time = np.mean(historical_times)

        # Species adjustment (from wood database lookup)
        # Example: Cottonwood factor = 0.92, Oak factor = 1.15
        species_factor = wood_df[
            wood_df['species'] == species
        ]['difficulty_multiplier'].values[0]

        # Quality adjustment (0-10 scale -> percentage adjustment)
        # Formula: quality_factor = 1.0 + ((quality - 5) * 0.02)
        # Quality 5 (average): 1.0 (no adjustment)
        # Quality 8 (hard): 1.06 (+6% slower)
        # Quality 2 (soft): 0.94 (-6% faster)
        quality_factor = 1.0 + ((quality - 5) * 0.02)

        # Diameter adjustment (relative to standard 380mm)
        # Formula: diameter_factor = (diameter / 380.0)
        # 380mm: 1.0 (no adjustment)
        # 450mm: 1.18 (+18% slower - more wood to cut)
        # 320mm: 0.84 (-16% faster - less wood)
        diameter_factor = diameter / 380.0

        # Confidence penalty (less data = add safety margin)
        # 3-4 times: +2s penalty
        # 5-7 times: +1s penalty
        # 8+ times: +0s penalty
        if len(historical_times) < 5:
            confidence_penalty = 2.0
        elif len(historical_times) < 8:
            confidence_penalty = 1.0
        else:
            confidence_penalty = 0.0

        # Final calculation
        predicted_time = (base_time * species_factor *
                         quality_factor * diameter_factor +
                         confidence_penalty)

        return predicted_time

CONCRETE EXAMPLE:
-----------------
Competitor: John Smith
Event: Standing Block
Historical times (SB): [32.1, 33.8, 31.5, 34.2, 32.9, 31.8, 33.1, 32.4]
Today's wood: Cottonwood, 380mm, Quality 7

CALCULATION STEPS:
  base_time = AVERAGE([32.1, 33.8, 31.5, 34.2, 32.9, 31.8, 33.1, 32.4])
            = 32.725 seconds

  species_factor = 0.92  (Cottonwood is soft, 8% faster than baseline)

  quality_factor = 1.0 + ((7 - 5) x 0.02) = 1.04  (Quality 7 = +4% harder)

  diameter_factor = 380 / 380 = 1.0  (standard size, no adjustment)

  confidence_penalty = 0.0  (8 historical times = high confidence)

  predicted_time = 32.725 x 0.92 x 1.04 x 1.0 + 0.0
                 = 31.3 seconds

RESULT: Baseline predicts John will cut in 31.3 seconds

? "See? Just arithmetic. No magic involved... unlike the next two methods!"
""")

    input("\nPress Enter to learn about LLM prediction...\n")

    print("=" * 70)
    print("  SPELL #2: LLM PREDICTION (AI SORCERY)")
    print("=" * 70)

    print("""
? "Now we enter TRUE sorcery - Large Language Models. This spell summons
an AI entity (running on Ollama) to make intelligent predictions."

HOW LLM PREDICTION WORKS:
--------------------------

The LLM method doesn't use formulas. Instead, it:
1. Constructs a detailed prompt describing the prediction task
2. Sends prompt to Ollama API (local AI server on localhost:11434)
3. Receives natural language response from AI
4. Parses the response to extract predicted time
5. Validates prediction is reasonable (5-300 seconds)

ACTUAL CODE (from FunctionsLibrary.py):
---------------------------------------

    def predict_competitor_time_with_ai(competitor_name, species, diameter,
                                       quality, event, results_df):
        # Get competitor's historical times
        competitor_data = results_df[
            results_df['competitor_name'] == competitor_name
        ]

        if len(competitor_data) < 3:
            return None  # Need minimum data for LLM

        # Calculate stats for prompt
        event_times = competitor_data[
            competitor_data['event'] == event
        ]['raw_time'].values

        avg_time = np.mean(event_times)
        recent_trend = "improving" if recent_avg < overall_avg else "stable"

        # Get wood properties
        wood_info = wood_df[wood_df['species'] == species].iloc[0]
        janka_hardness = wood_info['janka_hardness']
        spec_gravity = wood_info['specific_gravity']

        # Construct detailed prompt for AI
        prompt = f\"\"\"You are an expert woodchopping handicapper with decades
        of experience. Predict the cutting time for this competitor.

        COMPETITOR: {competitor_name}
        Historical {event} times: {list(event_times)}
        Average time: {avg_time:.1f} seconds
        Performance trend: {recent_trend}
        Total experience: {len(competitor_data)} recorded events

        TODAY'S WOOD:
        Species: {species}
        Janka hardness: {janka_hardness} lbf (higher = harder to cut)
        Specific gravity: {spec_gravity} (higher = denser wood)
        Diameter: {diameter}mm
        Quality rating: {quality}/10
          (0=rotten/soft, 5=average firmness, 10=exceptionally hard)

        TASK:
        Predict this competitor's cutting time in seconds accounting for:
        - Their historical performance and recent trend
        - Wood species characteristics (hardness and density)
        - Quality rating (firmness of THIS specific block)
        - Block diameter (more wood = longer time)

        Respond with ONLY a number (predicted seconds with 1 decimal).
        Then explain your reasoning in 1-2 sentences.

        Format: "Predicted time: XX.X seconds. Reasoning: ..."
        \"\"\"

        # Send to Ollama API
        response = call_ollama(prompt, model="qwen2.5:7b")

        # Parse response
        # Expected format: "Predicted time: 31.8 seconds. Reasoning: ..."
        match = re.search(r'(\\d+\\.\\d+)\\s*seconds', response)
        if match:
            predicted_time = float(match.group(1))

            # Validate (must be reasonable)
            if 5.0 <= predicted_time <= 300.0:
                return predicted_time

        return None  # Parsing failed

    def call_ollama(prompt, model="qwen2.5:7b"):
        \"\"\"Send prompt to local Ollama API and get response.\"\"\"
        import requests
        import json

        url = "http://localhost:11434/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            return result.get('response', '')

        except requests.exceptions.RequestException:
            return None  # Ollama not running or error

EXAMPLE LLM INTERACTION:
------------------------

SENT TO AI:
  [Full prompt as shown above for John Smith on Cottonwood...]

AI RESPONSE:
  "Predicted time: 31.4 seconds. Reasoning: John's recent performances
   show improving form (last 3 events averaged 31.8s). Cottonwood is
   a favorable species for his cutting style, and while Quality 7
   indicates slightly firmer grain than average (+0.3s expected), his
   improving technique compensates (-0.7s). The 380mm diameter is
   standard with no adjustment needed."

PARSED RESULT:
  predicted_time = 31.4 seconds

? "The AI considers nuances that formulas miss - like 'improving form' and
'favorable species for cutting style'. But it requires Ollama to be running
and takes 2-5 seconds per prediction. Worth it for the accuracy boost!"
""")

    input("\nPress Enter to learn about ML prediction...\n")

    print("=" * 70)
    print("  SPELL #3: ML PREDICTION (GRADIENT BOOSTING WIZARDRY)")
    print("=" * 70)

    print("""
? "The ML method is my MASTER-LEVEL spell. It uses XGBoost - one of the most
powerful prediction algorithms known to data science. Buckle up!"

THE ML PIPELINE (5 STAGES):
----------------------------

STAGE 1: DATA PREPARATION
  - Load ALL historical results from database
  - Validate data (remove outliers, check for errors)
  - Split into two datasets: Standing Block and Underhand

STAGE 2: FEATURE ENGINEERING
  For each historical result, calculate 6 features:

  Feature 1: competitor_avg_time_by_event
    -> Competitor's historical average for this event type

  Feature 2: event_encoded
    -> 0 for Standing Block, 1 for Underhand

  Feature 3: size_mm
    -> Block diameter in millimeters

  Feature 4: wood_janka_hardness
    -> Wood hardness rating (from species lookup)

  Feature 5: wood_spec_gravity
    -> Wood density (from species lookup)

  Feature 6: competitor_experience
    -> Count of competitor's past events

STAGE 3: MODEL TRAINING (SEPARATE SB AND UH MODELS)
  For each event type:
    1. Split data into training/validation sets (5-fold CV)
    2. Train XGBoost with these hyperparameters:
       - n_estimators = 100 (build 100 decision trees)
       - max_depth = 4 (prevent overfitting)
       - learning_rate = 0.1 (conservative learning)
       - objective = 'reg:squarederror' (minimize squared error)
    3. Validate on held-out data
    4. Calculate feature importance (which features matter most)

STAGE 4: PREDICTION
  For new competitor:
    1. Calculate their 6 features
    2. Feed to appropriate model (SB or UH)
    3. Model outputs predicted time
    4. Validate prediction is reasonable

STAGE 5: CONFIDENCE ASSESSMENT
  Based on training data size:
    - 80+ records: HIGH confidence
    - 50-79 records: MEDIUM confidence
    - 30-49 records: LOW confidence
    - <30 records: Don't use ML (fall back to LLM/Baseline)

ACTUAL CODE (simplified from FunctionsLibrary.py):
--------------------------------------------------

    import xgboost as xgb
    from sklearn.model_selection import cross_val_score

    def train_ml_model(results_df, event_type):
        \"\"\"Train XGBoost model for given event type.\"\"\"

        # Filter to this event type
        event_data = results_df[results_df['event'] == event_type]

        if len(event_data) < 30:
            return None  # Insufficient training data

        # Engineer features for each row
        features_df = engineer_features_for_ml(event_data, wood_df)

        # Features (X) and target (y)
        X = features_df[[
            'competitor_avg_time_by_event',
            'event_encoded',
            'size_mm',
            'wood_janka_hardness',
            'wood_spec_gravity',
            'competitor_experience'
        ]]
        y = features_df['raw_time']  # Actual cutting times

        # Create XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            objective='reg:squarederror',
            random_state=42
        )

        # Train with cross-validation
        cv_scores = cross_val_score(
            model, X, y,
            cv=5,  # 5-fold cross-validation
            scoring='neg_mean_squared_error'
        )

        # Train on full dataset
        model.fit(X, y)

        # Get feature importance
        importance = model.feature_importances_

        return model, importance, cv_scores

    def predict_with_ml(competitor_name, species, diameter,
                       quality, event, results_df):
        \"\"\"Make prediction using trained ML model.\"\"\"

        # Get appropriate model (SB or UH)
        if event == 'SB':
            model = cached_ml_model_sb
        else:
            model = cached_ml_model_uh

        if model is None:
            return None  # Model not trained yet

        # Calculate competitor's features
        competitor_history = results_df[
            (results_df['competitor_name'] == competitor_name) &
            (results_df['event'] == event)
        ]

        if len(competitor_history) == 0:
            return None  # No history for this event

        # Feature 1: Historical average
        competitor_avg = np.mean(competitor_history['raw_time'])

        # Feature 2: Event encoding
        event_encoded = 0 if event == 'SB' else 1

        # Feature 3: Size
        size_mm = diameter

        # Feature 4 & 5: Wood properties (lookup)
        wood_row = wood_df[wood_df['species'] == species].iloc[0]
        janka = wood_row['janka_hardness']
        spec_grav = wood_row['specific_gravity']

        # Feature 6: Experience
        experience = len(results_df[
            results_df['competitor_name'] == competitor_name
        ])

        # Combine into feature vector
        features = np.array([[
            competitor_avg,    # Feature 1
            event_encoded,     # Feature 2
            size_mm,          # Feature 3
            janka,            # Feature 4
            spec_grav,        # Feature 5
            experience        # Feature 6
        ]])

        # Predict
        predicted_time = model.predict(features)[0]

        # Validate
        if 5.0 <= predicted_time <= 300.0:
            return predicted_time

        return None

HOW XGBOOST WORKS (CONCEPTUALLY):
----------------------------------

XGBoost builds an ensemble of 100 decision trees, each learning from
the previous tree's mistakes:

Tree 1: Makes initial predictions (often just the average)
  -> Error: Some predictions too high, some too low

Tree 2: Learns to predict Tree 1's errors
  -> Prediction = Tree 1 + 0.1 x Tree 2
  -> Better predictions, but still some error

Tree 3: Learns to predict remaining errors
  -> Prediction = Tree 1 + 0.1 x Tree 2 + 0.1 x Tree 3
  -> Even better...

... repeat 100 times ...

Tree 100: Tiny corrections to nearly-perfect predictions
  -> Final prediction = Tree 1 + 0.1 x (Tree 2 + ... + Tree 100)

Each tree is a simple decision tree like:

    Is competitor_avg < 35 seconds?
    +- YES: Is janka_hardness < 600?
    |  +- YES: Predict 29.2 seconds
    |  +- NO:  Predict 32.8 seconds
    +- NO: Is experience > 5?
       +- YES: Predict 38.1 seconds
       +- NO:  Predict 41.3 seconds

100 of these trees vote together -> highly accurate prediction!

CONCRETE EXAMPLE:
-----------------
Competitor: John Smith
Event: Standing Block
Today's wood: Cottonwood 380mm, Quality 7

FEATURE CALCULATION:
  Feature 1 (competitor_avg): 32.7s (John's SB historical average)
  Feature 2 (event_encoded): 0 (Standing Block)
  Feature 3 (size_mm): 380
  Feature 4 (janka_hardness): 430 (Cottonwood)
  Feature 5 (spec_gravity): 0.40 (Cottonwood)
  Feature 6 (experience): 12 (John has 12 total events)

FEED TO ML MODEL:
  features = [32.7, 0, 380, 430, 0.40, 12]

  Model processes through 100 trees:
  Tree 1: 32.5s
  Tree 2 correction: -0.3s -> 32.2s
  Tree 3 correction: -0.2s -> 32.0s
  ...
  Tree 100 correction: -0.01s -> 31.2s

  FINAL PREDICTION: 31.2 seconds

WHY ML IS MOST ACCURATE:
  - Learns ACTUAL patterns from 100+ historical results
  - Captures complex interactions (e.g., "experienced competitors
    handle hard wood better than formulas predict")
  - No human bias in adjustment factors
  - Validated with cross-validation to prevent overfitting

? "ML is the most powerful spell in my grimoire, but it requires substantial
training data (30+ records). When available, it outperforms both Baseline
and LLM methods. That's why it's the top priority in prediction selection!"
""")

    input("\nPress Enter to learn how handicap marks are calculated...\n")

    print("=" * 70)
    print("  SPELL #4: HANDICAP MARK CALCULATION")
    print("=" * 70)

    print("""
? "Once we have predicted times, converting them to handicap marks is
surprisingly simple. But it follows strict AAA competition rules!"

AAA HANDICAP RULES:
-------------------
1. Slowest predicted competitor gets Mark 3 (front marker)
2. Mark = 3 + (gap from slowest) rounded UP to whole seconds
3. Maximum time limit: 180 seconds (Mark cannot exceed 183)
4. Competitor must start when their mark is called
5. All competitors theoretically finish at the same time

ALGORITHM:
----------

1. Sort all competitors by predicted time (slowest to fastest)
2. slowest_time = predicted_time of first competitor
3. FOR each competitor:
       gap = slowest_time - competitor.predicted_time
       mark = 3 + ROUND_UP(gap)
       IF mark > 183:
           mark = 183  # Enforce maximum
       competitor.mark = mark

ACTUAL CODE:
------------

    def calculate_handicap_marks(competitors_with_predictions):
        \"\"\"Convert predicted times to handicap marks per AAA rules.\"\"\"

        # Sort by predicted time (slowest first)
        sorted_comps = sorted(
            competitors_with_predictions,
            key=lambda x: x['predicted_time'],
            reverse=True  # Descending: slowest first
        )

        # Slowest competitor is front marker
        slowest_time = sorted_comps[0]['predicted_time']

        # Calculate marks
        for comp in sorted_comps:
            gap = slowest_time - comp['predicted_time']

            # Round UP (ceiling logic: add 0.999 then int() truncates)
            mark = 3 + int(gap + 0.999)

            # Enforce 180-second maximum time limit
            if mark > 183:
                mark = 183

            comp['mark'] = mark

        return sorted_comps

CONCRETE EXAMPLE:
-----------------

Heat with 5 competitors (after predictions):

    Name              Predicted Time    Gap from Slowest    Handicap Mark
    --------------    --------------    ----------------    -------------
    Sue Johnson       58.3s             0.0s                Mark 3
    Bob Wilson        52.7s             5.6s -> 6s           Mark 9
    Amy Chen          48.2s             10.1s -> 11s         Mark 14
    Joe Smith         42.8s             15.5s -> 16s         Mark 19
    Dan Martinez      38.1s             20.2s -> 21s         Mark 24

STEP-BY-STEP CALCULATION:

Sue Johnson (slowest):
  gap = 58.3 - 58.3 = 0.0s
  mark = 3 + ⌈0.0⌉ = 3 + 0 = Mark 3
  -> Sue starts immediately when "Mark 3!" is called

Bob Wilson:
  gap = 58.3 - 52.7 = 5.6s
  mark = 3 + ⌈5.6⌉ = 3 + 6 = Mark 9
  -> Bob waits 6 seconds, starts when "Mark 9!" is called

Amy Chen:
  gap = 58.3 - 48.2 = 10.1s
  mark = 3 + ⌈10.1⌉ = 3 + 11 = Mark 14
  -> Amy waits 11 seconds, starts at "Mark 14!"

Joe Smith:
  gap = 58.3 - 42.8 = 15.5s
  mark = 3 + ⌈15.5⌉ = 3 + 16 = Mark 19
  -> Joe waits 16 seconds, starts at "Mark 19!"

Dan Martinez (fastest):
  gap = 58.3 - 38.1 = 20.2s
  mark = 3 + ⌈20.2⌉ = 3 + 21 = Mark 24
  -> Dan waits 21 seconds, starts at "Mark 24!"

THEORETICAL FINISH TIMES (if predictions perfect):
  Sue: 0s delay + 58.3s cutting = 58.3s finish
  Bob: 6s delay + 52.7s cutting = 58.7s finish
  Amy: 11s delay + 48.2s cutting = 59.2s finish
  Joe: 16s delay + 42.8s cutting = 58.8s finish
  Dan: 21s delay + 38.1s cutting = 59.1s finish

  -> Everyone finishes within ~1 second (practically simultaneous!)

REAL-WORLD FINISH (with ±3s variation):
  Natural performance variation means actual finishes spread by 5-10s,
  creating exciting competition. Monte Carlo simulation validates that
  all competitors have ~equal win probability despite skill differences.

WHY ROUND UP (CEILING)?
  Rounding up is MORE FAIR than rounding to nearest. Example:

  Gap = 5.1 seconds
  Nearest: Round to 5s -> Mark 8
  Ceiling: Round to 6s -> Mark 9

  With ceiling, faster competitor gets slightly MORE delay (safer).
  This compensates for prediction uncertainty and prevents fast
  competitors from being under-handicapped.

? "And that, dear knowledge seeker, is how the magic TRULY works! No smoke,
no mirrors - just solid algorithms backed by statistics, AI, and machine
learning working together to create FAIR competition."
""")

    input("\nPress Enter to see The Wizard's final wisdom (and questionable life advice)...\n")

    print("\n" + "=" * 70)
    print("  🧙 THE WIZARD'S FINAL WISDOM (AND GENERAL RANTING) 🧙")
    print("=" * 70)

    print("""
🧙 "Congratulations! You've made it through my entire technical rant without
falling asleep! As a reward, let me share some ACTUAL INSIGHTS (plus a few
hot takes about statistics that nobody asked for):"

═══════════════════════════════════════════════════════════════════════════

1. WHY THREE PREDICTION METHODS? (Because We're Paranoid)

   Look, if I had a dollar for every time someone said "Why not just use
   ONE method?"... I'd have like $7, but still!

   - Baseline: The reliable friend who shows up on time but is boring
   - ML Model: The smart friend who's amazing when they remember stuff
   - LLM: The creative friend who might be making things up but SOUNDS smart

   We use all three because sometimes boring-but-reliable wins, sometimes
   you need the smart one, and sometimes creative interpretation saves the day.
   It's like having a diverse friend group but for ALGORITHMS.

2. TRANSPARENCY = "Please Don't Sue Us"

   Every prediction can be explained because:
   - We don't want angry competitors showing up with axes (literally)
   - Being able to say "Here's the math" stops 99% of arguments
   - If the prediction is wrong, at least everyone knows WHY

   Fun fact: In 150+ years, Australian handicappers never had to show their
   work. We're disrupting 150 years of "trust me bro" tradition!

3. MONTE CARLO = EXPENSIVE PARANOIA

   We run 1 MILLION simulated races because we're terrified of looking dumb.
   Could we get away with 10,000? Probably. But then some statistician would
   tweet "INSUFFICIENT SAMPLE SIZE" and we'd never live it down.

4. THE ±3 SECOND BREAKTHROUGH (Our One Good Idea)

   This is the only truly ORIGINAL contribution to handicapping science:
   Using ABSOLUTE variance instead of PROPORTIONAL variance.

   Previous systems: "Fast people vary by ±5%, slow people vary by ±5%"
   Our system: "Everyone varies by ±3 seconds because PHYSICS"

   Why? Because wood grain knots don't care if you're fast. Fatigue happens
   in seconds, not percentages. We tested this extensively and the results
   were like... WHOA. 31% win rate spread vs 6.7%. Chef's kiss.

5. THIS GETS SMARTER OVER TIME (Unlike Us)

   Every competition = more data = better ML model = more accurate predictions.
   The system learns. We, the developers, do not. We're still confused about
   why semicolons exist and whether tabs or spaces are correct (it's spaces,
   fight me).

═══════════════════════════════════════════════════════════════════════════

🧙 "REAL TALK: No handicapping system is perfect. Wood is weird. Axes are
unpredictable. Humans are chaotic meat puppets powered by breakfast and
spite. But STRATHEX is probably the most over-engineered, unnecessarily
complicated, absurdly transparent system ever created for predicting
lumber-based athletics.

We combined THREE AI systems, ran ONE MILLION simulations, wrote 3,500+
lines of code, and created this ENTIRE explanation system... just to answer
the question: 'Who should start first?'

Is it overkill? Absolutely. Are we proud of it? You bet your XGBoost we are."

🧙 "Now go forth and handicap with confidence! Or at least with DOCUMENTED
UNCERTAINTY, which is the best any of us can hope for in this cruel world."

         *    .    *  THE WIZARD   *    .    *
         .    *         .  HAS SPOKEN   .    *
         *    .    *  (FINALLY)    *    .    *

═══════════════════════════════════════════════════════════════════════════
""")

    input("\nPress Enter to return to menu...")


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    # Test the explanation menu
    print("\nTesting Explanation System Functions...")
    explanation_menu()
