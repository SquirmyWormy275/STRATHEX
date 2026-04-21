# Prediction Methods

STRATHEX runs three independent predictors for every competitor and picks the most accurate for each one. This page covers how each method works, when it's chosen, and how the selection logic decides.

---

## Method 1 — Baseline (statistical)

Always available. Pure math. No ML model required, no external service required.

### Inputs

- Competitor's historical times on this event (SB or UH)
- Wood species (for species hardness factor)
- Block diameter (for QAA scaling)
- Wood quality rating (0–10)
- Date of each historical result (for time-decay)

### Calculation

```
1. Pull all historical results for this competitor + event.
2. Apply exponential time-decay to each:
       weight = 0.5 ^ (days_old / 730)
3. Compute time-decay-weighted mean → base_time.
4. Scale diameter via QAA empirical tables:
       scaled_time = base_time × qaa_factor(from_diameter, to_diameter,
                                             effective_janka_hardness)
5. Apply wood quality adjustment:
       quality_factor = 1.0 + ((5 - quality) × 0.02)   # ±2% per quality point
       predicted_time = scaled_time × quality_factor
6. Add confidence penalty if data is sparse:
       N < 5:  +2.0s
       N < 8:  +1.0s
       N ≥ 8:  +0.0s
```

### Time-decay weighting

Every historical result is weighted by how recent it is, using an exponential decay with a **2-year half-life**:

| Years ago | Weight |
|---|---|
| 0 (current season) | 1.00 |
| 1 | 0.71 |
| 2 | 0.50 |
| 4 | 0.25 |
| 7 | 0.10 |
| 10 | 0.03 (effectively zero) |

This matters enormously for aging competitors. Without decay, a chopper's 19-second peak from 2018 dominates their current 29-second baseline, producing wildly optimistic predictions and under-handicapped marks. With decay, the system adjusts for age and current form automatically.

### Example

**Competitor:** John Smith · **Event:** Standing Block · **History:**

```
[32.1s @ 2025, 33.8s @ 2024, 31.5s @ 2023, 34.2s @ 2022,
 32.9s @ 2020, 31.8s @ 2019, 33.1s @ 2018, 32.4s @ 2015]
```

**Today's wood:** Cottonwood, 380mm, Quality 7

```
time-decay weighted mean     = 32.4s (recent years dominate)
diameter scaling             = 32.4s × 1.00 (380mm ≈ historical average)
quality factor (Q=7)         = 1.0 + ((5-7) × 0.02) = 0.96   ← Q7 is firmer, WAIT that's wrong direction
                                                                (see "quality convention" below)
```

### Quality convention

The quality scale is **0 = hardest, 10 = softest**:

| Quality | Meaning | Effect on time |
|---|---|---|
| 10 | Extremely soft (cuts fast) | baseline × 0.90 |
| 7 | Softer than average | baseline × 0.96 |
| 5 | Average | baseline × 1.00 |
| 3 | Firmer than average | baseline × 1.04 |
| 0 | Rock hard / extremely firm | baseline × 1.10 |

So Q=7 Cottonwood (softer than average) reduces time. The formula: `quality_factor = 1.0 + ((5 - quality) × 0.02)`, giving ±2% per quality point.

### Confidence

| Records available | Confidence | Used in selection |
|---|---|---|
| N ≥ 10 | HIGH | Normal |
| 5 ≤ N < 10 | MEDIUM | Normal |
| 3 ≤ N < 5 | LOW | Warning shown |
| N < 3 | N/A | **Blocked** — competitor can't be picked |

### Strengths

- Always available, no dependencies
- Transparent — judges can verify the calculation by hand
- Robust to small datasets
- No black box

### Weaknesses

- Doesn't capture interactions (e.g., "aging choppers struggle more on hardwood")
- Uniform adjustments across competitors — no personalization beyond the mean
- Slower to react to sudden form changes than the ML model

---

## Method 2 — ML (XGBoost)

Machine-learning predictor. **Preferred** method when sufficient training data exists.

### Model

XGBoost regressor. Two separate models — one for Standing Block, one for Underhand — trained on the full historical result database. Training configuration:

- 100 decision trees (gradient-boosted)
- Max depth 4 (prevents overfitting on small datasets)
- Learning rate 0.1
- 5-fold cross-validation for performance reporting
- Training weights use the same exponential time-decay as the baseline

### Features (23 total, V5.1)

| Category | Features |
|---|---|
| Core | `competitor_avg_time_by_event` (time-decay weighted), `event_encoded` (SB=0, UH=1), `size_mm` |
| Wood mechanics | Janka hardness, specific gravity, shear strength, crush strength, MOR, MOE |
| Competitor profile | experience count, trend slope, variance, median diameter, recency, career phase |
| Interactions | `diameter²`, `quality × diameter`, `quality × hardness`, `experience × size`, `event × diameter` |
| Seasonal | `month_sin`, `month_cos` |

Feature importance (SB model, current dataset):

```
competitor_avg_time_by_event    82.0%
competitor_experience            5.5%
size_mm                          5.3%
wood_spec_gravity                4.0%
wood_janka_hardness              3.2%
(other features, combined)       0.0%
```

Translation: who the competitor *is* dominates the prediction. Everything else is adjustment.

### Current performance (March 2026)

| Event | Records | MAE | R² |
|---|---|---|---|
| SB | 69 | 2.55s | 0.989 |
| UH | 35 | 2.35s | 0.878 |

SB has tight fit (high R²); UH is more variable because the training set is smaller.

### Confidence

| Training records | Confidence | Used |
|---|---|---|
| N ≥ 80 | HIGH | Normal |
| 50 ≤ N < 80 | MEDIUM | Normal |
| 30 ≤ N < 50 | LOW | Normal with warning |
| N < 30 | — | Not used (baseline instead) |

### Cross-diameter handling

If the competitor's historical results are mostly at one diameter (e.g., 325mm) and today's wood is a different diameter (275mm), the ML prediction is flagged as extrapolation. The selection logic (below) penalizes this and typically prefers the QAA-scaled baseline instead.

### Strengths

- Most accurate method when training data is sufficient
- Consistent — same input always produces same output
- Fast — milliseconds per prediction
- Learns complex interactions baseline can't capture

### Weaknesses

- Cold start — can't predict for brand new competitors
- Black box — harder to explain a specific prediction
- Requires retraining to absorb new data

---

## Method 3 — LLM (Ollama)

AI-reasoned prediction. Uses a local LLM (default: `qwen2.5:7b`) running on Ollama to apply a quality adjustment on top of the statistical baseline.

### How it works

1. Compute the baseline prediction.
2. Construct a prompt with:
   - Competitor's historical performance
   - Today's wood (species, hardness, specific gravity, diameter, quality)
   - Tournament context (if this is a semi/final using heat data at 97% weight)
3. Send to Ollama; parse the LLM's reasoning and extracted predicted time.
4. Validate: prediction must be within 5–300 seconds.
5. Fall back to pure baseline if Ollama is unavailable or the response doesn't parse.

The LLM sees the baseline number and is specifically prompted to apply a *quality adjustment*, not override the statistical prediction entirely. This is intentional — the baseline has 150+ years of competition-data credibility; the LLM's role is nuance (e.g., "this competitor's recent form suggests they're adapting well to harder wood").

### Prompt conventions

- Separate prompt templates for time prediction, fairness assessment, and championship race analysis. All three live in STRATHMARK (`llm_roles.py`).
- Tournament-weighted predictions use a dedicated prompt section warning the LLM that the baseline is already hyper-specific (today's exact wood), so adjustments should be minimal.
- All prompts versioned in [`docs/PROMPT_CHANGELOG.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PROMPT_CHANGELOG.md).

### Strengths

- Nuanced reasoning — captures subtle form trends or unusual wood conditions
- Provides human-readable justification for the prediction
- Only method that can meaningfully reason about wood quality beyond a single number

### Weaknesses

- Requires Ollama running locally (graceful fallback if missing)
- Slower (2–5s per competitor)
- Non-deterministic — same input can produce small variations
- Less reliable than ML for routine predictions on well-represented competitors

---

## Selection logic (V6.0)

The three predictors run in parallel; then STRATHMARK picks one via **expected-error scoring**:

```python
def score(prediction):
    score  = base_error(prediction.confidence)      # see table below
    score += 0.5  if prediction.method == "LLM"
    score += 1.5  if prediction.scaled
    score -= 1.0  if prediction.tournament_weighted  # floored at 0.5
    score += spread_penalty(all_three_predictions)
    return score

# Pick the prediction with the lowest score.
# Manual override always wins.
# Panel mark (if no predictions available) is last resort.
```

### Base error by confidence

| Confidence | Base error (seconds) |
|---|---|
| VERY HIGH | 2.0 |
| HIGH | 3.0 |
| MEDIUM | 5.0 |
| LOW | 7.0 |
| VERY LOW | 9.0 |

### Spread penalty

When the three methods disagree by ≥4 seconds or ≥12%, something's wrong — probably a data issue. Each prediction takes a +1 or +2 spread penalty, which cascades down and typically surfaces the issue in the approval UI so the Handicapper can investigate.

### Why this replaces the old fixed cascade

The V5.2 priority was hardcoded: **Baseline → ML → LLM → Panel**. But that's wrong in many cases. A LOW-confidence baseline shouldn't beat a HIGH-confidence ML prediction. A VERY HIGH tournament-weighted LLM prediction (competitor just ran a heat on this exact wood) should absolutely beat a generic baseline. Expected-error scoring makes the trade-off explicit and data-driven.

---

## Panel-mark fallback

If all three methods fail — typically because the competitor has too little history or the wood/event combination is totally unrepresented — STRATHMARK falls back to the **QAA panel mark**:

| Event | Panel mark |
|---|---|
| Open Standing Block / Underhand | 15 |
| Open Treefelling | 70 |
| Novice | 35 |
| Juniors | 15 |
| Sawing | 15 |
| Women's Underhand | 35 |
| Veterans | Set by handicapping committee |

(From the [QAA bylaws](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/QAA.pdf) §2.)

Panel marks are the conventional "I don't know anything about this competitor" default that the QAA has used for decades. They're deliberately a last resort — STRATHEX warns clearly when it's using them.

---

## How to tell which method was used

The approval UI shows all three predictions, the selected one, and the method name:

```
Competitor        Baseline    ML      LLM      Selected   Method     Confidence
──────────────────────────────────────────────────────────────────────────────────
Cole Schlenker    24.3s       24.1s   24.5s    24.1s      ML         HIGH
```

If a method returned no prediction (e.g., ML couldn't run because too few records), its column shows a dash. If all three were very close, the Method column confirms the choice; if they diverged, the Handicapper knows to look closer.

---

## Further reading

- [Handicap System Explained](Handicap-System-Explained) — the end-to-end pipeline
- [Monte Carlo Fairness](Monte-Carlo-Fairness) — validating the predictions
- [docs/ML_AUDIT_REPORT.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/ML_AUDIT_REPORT.md) — ML model audit detail
- [docs/PROMPT_ENGINEERING_GUIDELINES.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PROMPT_ENGINEERING_GUIDELINES.md) — LLM prompt conventions
