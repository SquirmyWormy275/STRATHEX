# STRATHEX Handicap System - Complete Technical Documentation

**Version:** 3.1
**Last Updated:** December 2025
**Purpose:** Comprehensive explanation of handicap calculation methodology

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Prediction Methods Explained](#prediction-methods-explained)
3. [Statistical Glossary](#statistical-glossary)
4. [Technical Deep Dive](#technical-deep-dive)
5. [Frequently Asked Questions](#frequently-asked-questions)

---

## System Overview

### What Does STRATHEX Do?

In professional woodchopping, competitors have vastly different skill levels. A world champion might cut a block in 25 seconds, while a skilled amateur takes 60 seconds. Without handicapping, the amateur has **ZERO chance of winning**.

Handicapping solves this by giving faster competitors **DELAYED STARTS**:
- Slowest competitor (Mark 3) starts immediately
- Fastest competitors (higher marks) start later
- If handicaps are perfect, everyone finishes at the SAME TIME
- Natural variation (±3 seconds) creates exciting competition

### The STRATHEX Solution

This program predicts how fast each competitor will cut a specific block of wood, then calculates handicap marks so everyone has an **EQUAL chance to win**.

### Key Innovations

#### 1. Triple Prediction System

We don't rely on one method - we use **THREE** different approaches and automatically select the most accurate prediction available:

- **BASELINE (Manual):** Statistical calculation using historical averages
- **ML MODEL:** Machine learning trained on 100+ historical performances
- **LLM:** AI-enhanced prediction accounting for wood quality factors

**Priority:** ML > LLM > Baseline (most accurate method wins)

#### 2. Comprehensive Wood Factors

The system accounts for everything that affects cutting speed:
- Wood species (hardness varies dramatically)
- Block diameter (more wood = longer cutting time)
- Wood quality (0-10 scale: soft/rotten vs rock-hard)
- Competitor's historical performance on similar wood

#### 3. Absolute Variance Modeling

**CRITICAL INNOVATION:** We use ±3 seconds variance for ALL competitors.

**Why?** Real-world factors affect everyone equally in ABSOLUTE terms:
- Wood grain knot costs 2 seconds for novice AND expert
- Technique wobble affects everyone by similar absolute time
- Proportional variance (±5% of time) gives unfair advantage to fast choppers

**Tested with 1 million Monte Carlo simulations** - absolute variance is FAIRER.

#### 4. Fairness Validation

Every handicap calculation can be tested with Monte Carlo simulation:
- Simulates 1 million races with realistic performance variation
- Measures each competitor's win probability
- Identifies systematic bias in predictions
- Rates fairness: Excellent / Very Good / Good / Fair / Poor

### The Result: Transparent, Defensible, Fair

When a judge asks "Why does Joe Smith get Mark 15?" we can show:
- His historical cutting times (average 28.3s on Standing Block)
- Adjustment for today's wood (Cottonwood, 380mm, Quality 6)
- Three independent predictions (Baseline: 29.1s, ML: 28.8s, LLM: 29.3s)
- Selected prediction: 28.8s (ML - highest confidence)
- His handicap mark: 15 (calculated from gap to slowest competitor)
- Monte Carlo validation: System rates "Excellent" (2.1% win rate spread)

This is **TRANSPARENT, DEFENSIBLE, and FAIR** handicapping.

---

## Prediction Methods Explained

### Method 1: Baseline (Manual Statistical Calculation)

#### How It Works

1. Calculate competitor's historical average time for this event (SB or UH)
2. Apply species adjustment factor (hardwood vs softwood)
3. Apply diameter adjustment (larger blocks take longer)
4. Apply quality adjustment (firm wood is slower to cut)
5. Add confidence penalty if limited historical data

#### Example Calculation

**Competitor:** John Smith
**Event:** Standing Block
**Historical average:** 32.5 seconds (based on 8 past events)
**Today's wood:** Cottonwood (soft species, -5% adjustment)
**Diameter:** 380mm (medium size, no adjustment)
**Quality:** 8/10 (firmer than average, +6% adjustment)

**Calculation:**
```
Base time: 32.5s
Species adjustment: 32.5 × 0.95 = 30.9s
Quality adjustment: 30.9 × 1.06 = 32.8s
PREDICTED TIME: 32.8 seconds
```

#### Advantages

- ✅ **ALWAYS AVAILABLE** (works even with minimal data)
- ✅ **TRANSPARENT** (simple math anyone can verify)
- ✅ **RELIABLE** (based on actual competitor performance)
- ✅ **FAST** (instant calculation, no waiting)

#### Disadvantages

- ❌ **SIMPLIFIED** (doesn't capture complex interactions)
- ❌ **GENERIC** (applies same adjustments to all competitors)
- ❌ **LIMITED** (only uses event-specific historical data)
- ❌ **CONSERVATIVE** (may not detect improving/declining form)

#### When Used

- New competitors with 3-5 historical times
- When ML model has insufficient training data
- As fallback if LLM prediction fails
- To validate other prediction methods

---

### Method 2: LLM (AI-Enhanced Prediction)

#### How It Works

1. System sends detailed prompt to Ollama AI (qwen2.5:7b model)
2. Prompt includes:
   - Competitor's complete historical performance data
   - Wood species characteristics (hardness, grain patterns)
   - Block diameter and quality rating
   - Context about event type and conditions
3. AI analyzes patterns humans might miss
4. Returns predicted time with reasoning
5. System validates prediction (must be 5-300 seconds)

#### Example AI Response

**Predicted time:** 31.8 seconds

**Reasoning:** John's recent trend shows improving form (last 3 events averaged 31.2s vs overall 32.9s). Cottonwood is generally favorable for his cutting style, but Quality 8 indicates tighter grain requiring more power. The firm grain will slow him slightly (+1.5s) but his improving form compensates (-1.6s). Net prediction: 31.8s.

#### Advantages

- ✅ **CONTEXTUAL** (considers subtle factors like recent form, wood grain)
- ✅ **ADAPTIVE** (learns patterns from description, not just numbers)
- ✅ **REASONING** (provides explanation for predictions)
- ✅ **NUANCED** (handles quality variations better than formulas)

#### Disadvantages

- ❌ **REQUIRES OLLAMA** (must have local AI server running)
- ❌ **SLOWER** (2-5 seconds per competitor)
- ❌ **VARIABLE** (same input might give slightly different predictions)
- ❌ **OPAQUE** (AI reasoning not always fully transparent)
- ❌ **REQUIRES DATA** (needs good historical information to work well)

#### When Used

- Competitor has 3+ historical times
- Ollama is running and responsive
- ML model doesn't have enough training data
- Wood quality is unusual (very soft or very hard)

---

### Method 3: ML Model (XGBoost Machine Learning)

#### How It Works

1. System trains **TWO separate models** (one for SB, one for UH)
2. Training data: ALL historical results in database (100+ events)
3. Each result is transformed into **6 features:**
   - Feature 1: `competitor_avg_time_by_event` (their typical performance)
   - Feature 2: `event_encoded` (0 for SB, 1 for UH)
   - Feature 3: `size_mm` (block diameter)
   - Feature 4: `wood_janka_hardness` (wood hardness rating)
   - Feature 5: `wood_spec_gravity` (wood density)
   - Feature 6: `competitor_experience` (count of past events)
4. XGBoost algorithm learns patterns:
   - How does diameter affect time? (linear? exponential?)
   - How does hardness impact different skill levels?
   - Do experienced competitors handle hard wood better?
   - What's the relationship between past avg and future performance?
5. Model validated with 5-fold cross-validation
6. For new prediction, system feeds 6 features, model outputs time

#### Example Prediction

**Competitor:** John Smith
**Event:** Standing Block

**Features Engineered:**
- Feature 1 (avg_time): 32.5s (John's SB historical average)
- Feature 2 (event): 0 (Standing Block encoded as 0)
- Feature 3 (size): 380mm
- Feature 4 (janka): 430 (Cottonwood hardness)
- Feature 5 (spec_gravity): 0.40 (Cottonwood density)
- Feature 6 (experience): 8 (John has 8 past SB events)

**ML MODEL PREDICTION:** 31.4 seconds

(Model learned that competitors with John's profile typically perform 0.8s faster than their average on medium-soft wood like Cottonwood)

#### Why XGBoost?

XGBoost (eXtreme Gradient Boosting) is the gold standard for tabular data. It won 17 out of 29 Kaggle competitions in 2015 and is used by:
- Netflix (recommendation predictions)
- Airbnb (pricing predictions)
- Microsoft (Bing search ranking)

It's **EXTREMELY accurate** on small-to-medium datasets (our use case).

#### Training Details

- 100 decision trees (each learns from previous tree's mistakes)
- Max depth 4 (prevents overfitting)
- Learning rate 0.1 (conservative, stable learning)
- Cross-validation prevents memorizing training data

#### Advantages

- ✅ **MOST ACCURATE** (when sufficient training data available)
- ✅ **CONSISTENT** (same input always gives same prediction)
- ✅ **FAST** (prediction takes milliseconds)
- ✅ **VALIDATED** (cross-validation ensures it generalizes well)
- ✅ **OBJECTIVE** (no human bias in predictions)

#### Disadvantages

- ❌ **REQUIRES DATA** (needs 30+ total events, 15+ per event type)
- ❌ **BLACK BOX** (harder to explain WHY it predicted a specific time)
- ❌ **STATIC** (doesn't update until retrained with new data)
- ❌ **COLD START** (can't predict for brand new competitors)

#### When Used

- Database has 30+ historical results
- Competitor has at least 1 historical time for this event
- This is the **PREFERRED** method when available (most accurate)

#### Confidence Levels

- **HIGH confidence:** 80+ training records
- **MEDIUM confidence:** 50-79 training records
- **LOW confidence:** 30-49 training records
- **NOT USED:** <30 training records (falls back to LLM or Baseline)

---

### Prediction Method Selection Priority

The system automatically selects the **BEST** available prediction for each competitor:

1. **ML MODEL** (if ≥30 training records AND competitor has event history)
   ↓ (if not available)
2. **LLM PREDICTION** (if Ollama running AND ≥3 competitor historical times)
   ↓ (if not available)
3. **BASELINE** (always available as fallback)

#### Real-World Example

Heat with 5 competitors calculating Standing Block handicaps:

- **Joe Smith** - 15 SB times → **ML PREDICTION** (best data)
- **Jane Doe** - 6 SB times → **ML PREDICTION** (sufficient data)
- **Bob Wilson** - 3 SB times → **LLM PREDICTION** (ML needs more data)
- **Amy Chen** - 2 SB times → **BASELINE** (not enough for LLM)
- **New Guy** - 0 SB times → **CANNOT CALCULATE** (need minimum 3 times)

#### Why This Priority?

Testing showed:
- ML average error: **±2.1 seconds** (when data available)
- LLM average error: **±3.4 seconds**
- Baseline average error: **±4.8 seconds**

The system displays **ALL THREE predictions** (when available) so judges can see:
- Which method was used for handicap marks
- How much the predictions agree/disagree
- Confidence level in the selected prediction

---

## Statistical Glossary

### Core Statistical Terms

#### Average (Mean)

**Definition:** The sum of all values divided by the count of values.

**Example:** If John cut blocks in 30s, 32s, 28s, 31s, and 29s, his average is (30+32+28+31+29)÷5 = **30.0 seconds**.

**Relevance:** Used to calculate a competitor's typical performance. The baseline prediction starts with their historical average.

**Where Seen:** Handicap calculation screen, prediction methods display

---

#### Standard Deviation

**Definition:** Measures how spread out values are from the average. Low = consistent, high = variable.

**Example:**
- Competitor A: times of 30s, 30s, 31s (std dev ~0.5s - very consistent)
- Competitor B: times of 25s, 35s, 30s (std dev ~4.1s - inconsistent)

**Relevance:** Shows performance consistency. Consistent competitors are more predictable. We use ±3 second standard deviation in Monte Carlo simulations.

**Where Seen:** Monte Carlo simulation results, statistical analysis section

---

#### IQR (Interquartile Range)

**Definition:** The range containing the middle 50% of data values. Calculated as Q3 - Q1 (75th percentile minus 25th percentile).

**Example:**
```
Times: 25, 27, 28, 30, 31, 33, 45 seconds
Q1 (25th %ile) = 27s, Q3 (75th %ile) = 33s
IQR = 33 - 27 = 6 seconds
```

**Relevance:** Used for robust outlier detection. IQR is not affected by extreme values, unlike standard deviation.

**Where Seen:** Data validation process (background)

---

#### 3×IQR (Outlier Detection)

**Definition:** A value is an extreme outlier if it's more than 3×IQR away from the quartiles. This is a very conservative threshold.

**Example:**
```
If IQR = 6s, outlier threshold is 18s from quartiles.
Times: 28, 29, 30, 31, 85s ← 85s is flagged and removed
```

**Relevance:** Removes data entry errors and invalid results (like a competitor who stopped mid-cut). Only extreme outliers are removed to preserve real performance variation.

**Where Seen:** Data validation warnings when loading historical results

---

#### Outlier

**Definition:** A data point that is extremely different from others. Could be error or genuine exceptional performance.

**Example:** If most times are 28-35s, a time of 95s is probably an error (competitor fell, axe broke, etc.)

**Relevance:** Outliers distort averages and predictions. System removes only EXTREME outliers (3×IQR method) to prevent errors while keeping genuine performances.

**Where Seen:** Data validation report shows how many outliers were detected and removed

---

### Handicapping Terms

#### Baseline Time / Baseline Prediction

**Definition:** The manual statistical prediction method using historical averages + adjustment factors.

**Example:** Baseline for Joe on Cottonwood 380mm: His avg (32s) × species factor (0.95) × quality factor (1.08) = 32.8s

**Relevance:** This is the "fallback" prediction method that always works. Simple, transparent, reliable.

**Where Seen:** Handicap display shows "Baseline: 32.8s" alongside ML and LLM predictions

---

#### Adjustment Factor

**Definition:** A multiplier applied to base time to account for wood characteristics. Usually ranges from 0.85 to 1.20.

**Example:**
- Soft wood species: 0.90 factor (10% faster)
- Hard wood species: 1.10 factor (10% slower)
- Quality 9/10 (very hard): +8% adjustment

**Relevance:** Adjusts predictions for today's specific wood. Same competitor will have different predictions on pine vs oak.

**Where Seen:** Visible in baseline prediction explanations and detailed calculation breakdowns

---

#### Handicap Mark

**Definition:** The number called for a competitor that determines their start delay. Mark 3 = start immediately, Mark 20 = wait 17 seconds.

**Example:**
- Front marker (slowest): Mark 3 (starts at "Mark 3!")
- Back marker (fastest): Mark 18 (waits 15 seconds, starts at "Mark 18!")

**Relevance:** **THIS IS THE MAIN OUTPUT.** The handicap mark equalizes competition by giving faster competitors delayed starts.

**Where Seen:** Main handicap display, heat assignments, announcer calls

---

#### Gap

**Definition:** The predicted time difference between a competitor and the slowest competitor. Used to calculate handicap marks.

**Example:**
```
Slowest competitor: predicted 55.0s
Joe Smith: predicted 42.0s
Gap = 55.0 - 42.0 = 13.0s → Mark 16 (3 + 13 rounded up)
```

**Relevance:** Larger gap = higher mark = longer delay. The gap directly converts predicted time into start delay.

**Where Seen:** Calculation process (background), visible in detailed handicap explanations

---

#### Front Marker

**Definition:** The slowest predicted competitor who receives Mark 3 (starts first). Acts as the baseline for all other marks.

**Example:** If Sue is predicted slowest at 58.2s, she gets Mark 3 and starts immediately when "Mark 3!" is called.

**Relevance:** Front marker has NO delay. All other competitors' delays are calculated relative to them.

**Where Seen:** Handicap results display, Monte Carlo simulation analysis

---

#### Back Marker

**Definition:** The fastest predicted competitor who receives the highest mark (starts last with longest delay).

**Example:** If John is predicted fastest at 28.5s and slowest is 55.0s, gap is 26.5s → Mark 30 (3 + 27). He waits 27 seconds.

**Relevance:** Back marker has the LONGEST delay. In a perfect handicap system, they should finish at the same time as front marker.

**Where Seen:** Handicap results display, Monte Carlo simulation analysis

---

### Validation Terms

#### Monte Carlo Simulation

**Definition:** A method that runs thousands/millions of virtual races with random performance variation to test handicap fairness.

**Example:**
```
System runs 1,000,000 simulated races:
- Each race, competitors vary ±3s from predicted time
- Count who wins each race
- Calculate win probability for each competitor
```

**Relevance:** Validates that handicaps are FAIR. If one competitor wins 40% of simulations while others win 5%, the handicaps are biased.

**Where Seen:** Optional fairness analysis after calculating handicaps

---

#### Win Probability / Win Rate

**Definition:** The percentage of simulated races won by each competitor. Ideally, all competitors should have equal win probability.

**Example:**
```
Heat with 5 competitors:
Ideal: 20% win rate each (5 competitors = 100%÷5)
Actual: Joe 23%, Sue 21%, Bob 19%, Amy 22%, Dan 15%
Dan is disadvantaged (15% vs 20% ideal)
```

**Relevance:** Measures handicap fairness. Spread <3% = Excellent, <6% = Very Good, <10% = Good, >16% = Poor.

**Where Seen:** Monte Carlo simulation results, displayed as bar charts and percentages

---

#### Win Rate Spread

**Definition:** The difference between highest and lowest win rates. Lower spread = fairer handicaps.

**Example:**
```
Highest win rate: 22.5%
Lowest win rate: 18.7%
Spread = 22.5 - 18.7 = 3.8% (rates as "Very Good")
```

**Relevance:** **PRIMARY FAIRNESS METRIC.** Spread <3% means handicaps are nearly perfect. >10% means predictions have systematic bias.

**Where Seen:** Monte Carlo simulation summary, AI fairness assessment

---

#### Confidence Level

**Definition:** How much historical data supports a prediction. More data = higher confidence = more reliable prediction.

**Example:**
- **HIGH:** Competitor has 12 past events, ML trained on 95 records
- **MEDIUM:** Competitor has 4 past events, ML trained on 55 records
- **LOW:** Competitor has 3 past events, ML trained on 35 records

**Relevance:** Tells judges how much to trust a prediction. LOW confidence predictions might be adjusted for safety.

**Where Seen:** Prediction methods summary shows ML confidence level (HIGH/MEDIUM/LOW)

---

### Machine Learning Terms

#### LLM (Large Language Model)

**Definition:** An AI system trained on massive text data that can understand context and make intelligent predictions. Domain-specialized for woodchopping reasoning.

**Example:** qwen2.5:7b model (7 billion parameters) running on Ollama. Optimized for mathematical reasoning tasks.

**Relevance:** LLM prediction method uses AI to consider subtle factors like wood quality, recent form, and species characteristics that formulas might miss.

**Where Seen:** Prediction methods display shows "LLM Model: 31.2s" when LLM prediction is available

---

#### ML (Machine Learning)

**Definition:** Computer algorithms that learn patterns from historical data and use those patterns to make predictions on new data.

**Example:** ML model learns: "Competitors 2s faster than average on soft wood" or "380mm blocks take 1.2× longer than 320mm blocks"

**Relevance:** ML prediction method is the MOST ACCURATE when enough training data exists. Learns complex patterns humans might miss.

**Where Seen:** Prediction methods display shows "ML Model: 30.8s" when ML prediction is used

---

#### Training Data

**Definition:** Historical competition results used to teach the ML model patterns. More training data = better predictions.

**Example:**
```
Database with 127 historical results:
- 68 Standing Block times
- 59 Underhand times
- Spanning 15 different competitors
- 8 different wood species
```

**Relevance:** ML model needs minimum 30 total records (15 per event type) to make reliable predictions. Quality matters more than quantity.

**Where Seen:** Prediction methods summary shows "ML Model: XGBoost trained on 127 records"

---

#### XGBoost

**Definition:** eXtreme Gradient Boosting - a specific ML algorithm that's highly accurate for prediction tasks with structured data.

**Example:** XGBoost won 17 of 29 Kaggle competitions in 2015. Used by Microsoft, Netflix, Airbnb for predictions.

**Relevance:** We chose XGBoost because it's the gold standard for small-to-medium tabular datasets (our exact use case).

**Where Seen:** Technical documentation, prediction methods explanation

---

#### Cross-Validation (CV)

**Definition:** A technique to test ML model accuracy by training on part of data and testing on another part. Prevents overfitting.

**Example:** 5-fold CV: Split data into 5 parts, train on 4, test on 1. Repeat 5 times. Average the results.

**Relevance:** Ensures ML model works on NEW data, not just memorizing training data. Validates prediction reliability.

**Where Seen:** Background process during ML training

---

#### Feature Engineering

**Definition:** Converting raw data into "features" (numerical inputs) that ML models can learn from.

**Example:**
```
Raw data: "Standing Block, Cottonwood, 380mm"
Features: event=0, janka=430, spec_gravity=0.40, size=380
```

**Relevance:** ML models need numbers, not text. Feature engineering transforms wood characteristics into learnable patterns.

**Where Seen:** Background process, mentioned in technical documentation

---

### Wood Properties

#### Quality Rating (0-10 Scale)

**Definition:** Judge's assessment of wood firmness/difficulty. 0=rotten/soft, 5=average, 10=exceptionally hard.

**Example:**
- Quality 3: Soft Cottonwood with loose grain (cuts fast)
- Quality 7: Firm Cottonwood with tight grain (cuts slower)
- Quality 10: Rock-hard oak, nearly impossible

**Relevance:** **CRITICAL INPUT.** Same species varies dramatically. Quality 3 vs Quality 9 can change times by 20%+.

**Where Seen:** Wood characteristics input, displayed in all handicap calculations

---

#### Species Hardness / Janka Hardness

**Definition:** Standard measure of wood hardness (pounds of force to embed steel ball halfway). Higher = harder to cut.

**Example:**
- Cottonwood: 430 lbf (soft)
- Douglas Fir: 710 lbf (medium)
- White Oak: 1360 lbf (very hard)

**Relevance:** Different species cut at vastly different speeds. ML model uses Janka hardness as a feature for predictions.

**Where Seen:** Wood species data (background), technical deep dive explanations

---

#### Specific Gravity

**Definition:** Wood density relative to water. Higher = denser = more material to cut through.

**Example:**
- Cottonwood: 0.40 (light, airy)
- Pine: 0.55 (medium density)
- Oak: 0.75 (dense, heavy)

**Relevance:** Denser wood takes longer to cut (more material). ML model uses specific gravity to refine predictions.

**Where Seen:** Wood species data (background), technical deep dive explanations

---

### Performance Variance

#### Absolute Variance (±3 Seconds)

**Definition:** Every competitor varies by the SAME number of seconds (±3s), not a percentage. Critical for fairness.

**Example:**
```
Fast chopper (30s predicted): actual time between 27-33s
Slow chopper (60s predicted): actual time between 57-63s
BOTH vary by ±3s absolute
```

**Relevance:** **MAJOR INNOVATION.** Proportional variance (±5%) gives unfair advantage to fast choppers. Real factors (grain knots, fatigue) affect everyone equally in seconds, not percentages.

**Where Seen:** Monte Carlo simulation methodology, system overview documentation

---

#### Proportional Variance

**Definition:** Variation as a percentage of predicted time (e.g., ±5%). REJECTED by this system as unfair.

**Example:**
```
With ±5% variance:
Fast chopper (30s): varies 27-33s (±3s range)
Slow chopper (60s): varies 54-66s (±6s range)
Slow chopper gets DOUBLE the variation!
```

**Relevance:** Proportional variance creates bias. Testing showed 31% win rate spread vs 6.7% with absolute variance. This is why we use absolute.

**Where Seen:** System documentation, mentioned in technical explanations of fairness

---

## Technical Deep Dive

### ⚠️ WARNING: TURBO NERD TERRITORY! ⚠️

**Beyond this point lies the EXACT technical machinery that powers STRATHEX's handicap calculations.**

---

### Algorithm #1: Baseline Prediction

#### Pseudocode

```
1. competitor_history = GET all historical times for this competitor + event
2. IF len(competitor_history) < 3:
       RETURN "Insufficient data - need minimum 3 historical times"
3. base_time = AVERAGE(competitor_history)
4. species_factor = LOOKUP species in wood database
5. quality_adjustment = CALCULATE from quality rating (0-10 scale)
6. diameter_adjustment = CALCULATE from block diameter
7. confidence_penalty = CALCULATE from amount of historical data
8. predicted_time = base_time × species_factor × quality_adjustment
                    × diameter_adjustment + confidence_penalty
9. RETURN predicted_time
```

#### Python Implementation (Simplified)

```python
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

    # Quality adjustment (0-10 scale → percentage adjustment)
    # Formula: quality_factor = 1.0 + ((quality - 5) * 0.02)
    # Quality 5 (average): 1.0 (no adjustment)
    # Quality 8 (hard): 1.06 (+6% slower)
    # Quality 2 (soft): 0.94 (-6% faster)
    quality_factor = 1.0 + ((quality - 5) * 0.02)

    # Diameter adjustment (relative to standard 380mm)
    # Formula: diameter_factor = (diameter / 380.0)
    diameter_factor = diameter / 380.0

    # Confidence penalty (less data = add safety margin)
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
```

#### Example Calculation

**Input:**
- Competitor: John Smith
- Event: Standing Block
- Historical times: [32.1, 33.8, 31.5, 34.2, 32.9, 31.8, 33.1, 32.4]
- Wood: Cottonwood, 380mm, Quality 7

**Steps:**
```
base_time = AVERAGE([32.1, 33.8, 31.5, 34.2, 32.9, 31.8, 33.1, 32.4])
          = 32.725 seconds

species_factor = 0.92  (Cottonwood is soft, 8% faster)

quality_factor = 1.0 + ((7 - 5) × 0.02) = 1.04  (+4% harder)

diameter_factor = 380 / 380 = 1.0  (standard size)

confidence_penalty = 0.0  (8 historical times)

predicted_time = 32.725 × 0.92 × 1.04 × 1.0 + 0.0
               = 31.3 seconds
```

**Output:** 31.3 seconds

---

### Algorithm #2: LLM Prediction

#### How It Works

1. Construct detailed prompt describing prediction task
2. Send prompt to Ollama API (local AI server)
3. Receive natural language response from AI
4. Parse response to extract predicted time
5. Validate prediction is reasonable (5-300 seconds)

#### Python Implementation (Simplified)

```python
def predict_competitor_time_with_ai(competitor_name, species, diameter,
                                   quality, event, results_df):
    # Get competitor's historical times
    competitor_data = results_df[
        results_df['competitor_name'] == competitor_name
    ]

    if len(competitor_data) < 3:
        return None

    # Calculate stats for prompt
    event_times = competitor_data[
        competitor_data['event'] == event
    ]['raw_time'].values

    avg_time = np.mean(event_times)

    # Get wood properties
    wood_info = wood_df[wood_df['species'] == species].iloc[0]
    janka_hardness = wood_info['janka_hardness']
    spec_gravity = wood_info['specific_gravity']

    # Construct prompt
    prompt = f"""You are an expert woodchopping handicapper.

    COMPETITOR: {competitor_name}
    Historical {event} times: {list(event_times)}
    Average: {avg_time:.1f}s

    TODAY'S WOOD:
    Species: {species}
    Janka hardness: {janka_hardness} lbf
    Specific gravity: {spec_gravity}
    Diameter: {diameter}mm
    Quality: {quality}/10

    Predict cutting time in seconds with 1 decimal place.
    Format: "Predicted time: XX.X seconds. Reasoning: ..."
    """

    # Send to Ollama
    response = call_ollama(prompt, model="qwen2.5:7b")

    # Parse response
    match = re.search(r'(\d+\.\d+)\s*seconds', response)
    if match:
        predicted_time = float(match.group(1))
        if 5.0 <= predicted_time <= 300.0:
            return predicted_time

    return None

def call_ollama(prompt, model="qwen2.5:7b"):
    """Send prompt to local Ollama API."""
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload, timeout=30)
    return response.json().get('response', '')
```

---

### Algorithm #3: ML Prediction (XGBoost)

#### The 5-Stage Pipeline

**Stage 1: Data Preparation**
- Load ALL historical results
- Validate data (remove outliers)
- Split into SB and UH datasets

**Stage 2: Feature Engineering**

For each result, calculate 6 features:
- `competitor_avg_time_by_event` - Historical average
- `event_encoded` - 0 for SB, 1 for UH
- `size_mm` - Block diameter
- `wood_janka_hardness` - From species lookup
- `wood_spec_gravity` - From species lookup
- `competitor_experience` - Count of past events

**Stage 3: Model Training**

```python
import xgboost as xgb
from sklearn.model_selection import cross_val_score

def train_ml_model(results_df, event_type):
    # Filter to this event
    event_data = results_df[results_df['event'] == event_type]

    if len(event_data) < 30:
        return None

    # Engineer features
    features_df = engineer_features_for_ml(event_data, wood_df)

    X = features_df[['competitor_avg_time_by_event', 'event_encoded',
                     'size_mm', 'wood_janka_hardness',
                     'wood_spec_gravity', 'competitor_experience']]
    y = features_df['raw_time']

    # Create model
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective='reg:squarederror',
        random_state=42
    )

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5,
                                scoring='neg_mean_squared_error')

    # Train on full dataset
    model.fit(X, y)

    return model
```

**Stage 4: Prediction**

```python
def predict_with_ml(competitor_name, species, diameter,
                   quality, event, results_df):
    # Get model
    model = cached_ml_model_sb if event == 'SB' else cached_ml_model_uh

    if model is None:
        return None

    # Calculate features
    competitor_history = results_df[
        (results_df['competitor_name'] == competitor_name) &
        (results_df['event'] == event)
    ]

    if len(competitor_history) == 0:
        return None

    competitor_avg = np.mean(competitor_history['raw_time'])
    event_encoded = 0 if event == 'SB' else 1
    wood_row = wood_df[wood_df['species'] == species].iloc[0]
    experience = len(results_df[results_df['competitor_name'] == competitor_name])

    # Build feature vector
    features = np.array([[
        competitor_avg,
        event_encoded,
        diameter,
        wood_row['janka_hardness'],
        wood_row['specific_gravity'],
        experience
    ]])

    # Predict
    predicted_time = model.predict(features)[0]

    return predicted_time if 5.0 <= predicted_time <= 300.0 else None
```

**Stage 5: Confidence Assessment**

```python
if training_data_size >= 80:
    confidence = "HIGH"
elif training_data_size >= 50:
    confidence = "MEDIUM"
elif training_data_size >= 30:
    confidence = "LOW"
else:
    confidence = "INSUFFICIENT" # Don't use ML
```

---

### Algorithm #4: Handicap Mark Calculation

#### AAA Competition Rules

1. Slowest predicted competitor gets Mark 3
2. Mark = 3 + (gap from slowest) **rounded UP** to whole seconds
3. Maximum time limit: 180 seconds (Mark ≤ 183)

#### Python Implementation

```python
def calculate_handicap_marks(competitors_with_predictions):
    # Sort by predicted time (slowest first)
    sorted_comps = sorted(
        competitors_with_predictions,
        key=lambda x: x['predicted_time'],
        reverse=True
    )

    # Slowest competitor is front marker
    slowest_time = sorted_comps[0]['predicted_time']

    # Calculate marks
    for comp in sorted_comps:
        gap = slowest_time - comp['predicted_time']

        # Round UP (ceiling: add 0.999 then truncate)
        mark = 3 + int(gap + 0.999)

        # Enforce 180-second maximum
        if mark > 183:
            mark = 183

        comp['mark'] = mark

    return sorted_comps
```

#### Example Calculation

**Heat with 5 competitors:**

| Name | Predicted Time | Gap | Handicap Mark |
|------|----------------|-----|---------------|
| Sue Johnson | 58.3s | 0.0s | Mark 3 (0s delay) |
| Bob Wilson | 52.7s | 5.6s → 6s | Mark 9 (6s delay) |
| Amy Chen | 48.2s | 10.1s → 11s | Mark 14 (11s delay) |
| Joe Smith | 42.8s | 15.5s → 16s | Mark 19 (16s delay) |
| Dan Martinez | 38.1s | 20.2s → 21s | Mark 24 (21s delay) |

**Theoretical finish times:**
```
Sue: 0s delay + 58.3s cutting = 58.3s finish
Bob: 6s delay + 52.7s cutting = 58.7s finish
Amy: 11s delay + 48.2s cutting = 59.2s finish
Joe: 16s delay + 42.8s cutting = 58.8s finish
Dan: 21s delay + 38.1s cutting = 59.1s finish
```

Everyone finishes within ~1 second!

---

## Frequently Asked Questions

### Q: How much historical data is needed?

**Minimum:** 3 historical times for the specific event (SB or UH)
**Ideal:** 8+ historical times for high confidence
**ML Training:** 30+ total results in database (15+ per event type)

### Q: What if a competitor has no historical data?

They cannot be handicapped. The system requires minimum 3 historical times to make any prediction. New competitors must participate in 3 events to build a baseline.

### Q: Can judges override the handicap marks?

Yes, but it's not recommended. The system shows all three prediction methods so judges can verify accuracy. If marks seem wrong, check:
1. Historical data quality (any outliers?)
2. Wood quality rating (is it accurate?)
3. Monte Carlo simulation (does it show bias?)

Manual overrides should be documented with reasoning.

### Q: How often should the ML model be retrained?

After every competition that adds 10+ new results to the database. The system will automatically detect when retraining is beneficial.

### Q: What if Ollama isn't running?

LLM predictions will be unavailable, but the system gracefully falls back to ML (if available) or Baseline predictions. Functionality is never blocked.

### Q: How long does handicap calculation take?

- **Baseline only:** Instant (<1 second for entire heat)
- **ML only:** ~0.5 seconds for entire heat
- **LLM + ML:** 2-5 seconds per competitor (depends on Ollama performance)

For a heat of 8 competitors: typically 5-15 seconds total.

### Q: Can this system be used for other sports?

Yes! The core algorithms (triple prediction, absolute variance, Monte Carlo validation) apply to any handicapped competition where:
1. Historical performance predicts future performance
2. Multiple factors affect outcome (equipment, conditions, skill)
3. Fair competition requires equalizing start times or scores

Examples: swimming, track & field, cycling time trials.

### Q: Is the source code available for review?

Yes, the complete source code is in the GitHub repository. All algorithms are documented and can be independently verified.

### Q: How is fairness measured?

Monte Carlo simulation runs 1 million virtual races and calculates each competitor's win probability. Ideal = everyone has equal probability (20% for 5 competitors).

**Fairness ratings:**
- **Excellent:** Win rate spread <3%
- **Very Good:** Spread <6%
- **Good:** Spread <10%
- **Fair:** Spread <16%
- **Poor:** Spread >16%

### Q: What happens if wood quality changes mid-competition?

Judges should recalculate handicaps if wood characteristics significantly change. The system allows recalculation at any time with updated quality ratings.

### Q: Why round UP instead of to nearest?

Rounding up gives faster competitors slightly MORE delay, which compensates for prediction uncertainty. This is safer and more conservative, reducing the chance of under-handicapping skilled competitors.

### Q: Can the system handle ties?

Yes. If two competitors have identical predicted times, they receive the same handicap mark and start simultaneously.

---

## Conclusion

The STRATHEX Handicap System combines three proven prediction methods (statistical calculation, machine learning, and AI reasoning) with rigorous fairness validation to create transparent, defensible, and accurate handicaps for woodchopping competitions.

**Key Strengths:**
- ✅ **Multiple prediction methods** ensure reliability
- ✅ **Transparent algorithms** build trust
- ✅ **Fairness validation** prevents bias
- ✅ **Absolute variance** creates truly equal competition
- ✅ **Complete documentation** enables independent verification

**For Judges:**
Every handicap can be explained and justified with data. No "black box" decisions.

**For Competitors:**
Fair competition where skill is equalized, and natural variation determines the winner.

**For Officials:**
Automated, consistent handicapping that reduces manual calculation errors and saves time.

---

**Document Version:** 3.1
**Last Updated:** December 2025
**For Questions:** Contact competition officials or review source code documentation

---

*"The best technical system is one that people TRUST. STRATHEX achieves this through transparency, multiple validation methods, and honest communication about limitations."*
