# Monte Carlo Fairness Validation

Predictions are estimates. Even the best prediction is wrong by a few seconds on any given day. Monte Carlo simulation asks: *given that the predictions are imperfect, how fair are the resulting handicaps?*

---

## The idea

Run the race many times — once, a thousand times, two million times — with each competitor's predicted time randomly varying within a plausible range. Count who wins. If the handicaps are fair, every competitor wins roughly equally often. If one competitor wins 35% of the simulations and another wins 12%, the handicaps are biased and the underperforming competitor got a raw deal.

## The variance model

**Each competitor's time varies by ±3 seconds absolute, drawn from a Gaussian distribution.**

This is the most consequential methodological decision in STRATHEX. It's also the most contested one. Here's the reasoning.

### Why absolute variance?

Alternative: **proportional variance** (say, ±5% of predicted time).

With proportional variance:
- A 30-second chopper has a range of 27–33s (±3s)
- A 60-second chopper has a range of 54–66s (±6s)

The slow chopper gets *double* the random range. In Monte Carlo terms, they win more often simply because their noise envelope is wider. That's not fair — it's bias.

With absolute variance:
- Every competitor's time varies by ±3s
- Everyone gets the same noise envelope

**Testing (1M simulations across many events):**

| Variance model | Win-rate spread |
|---|---|
| Proportional (±5%) | 31% |
| Absolute (±3s) | 6.7% |

Absolute variance is measurably, enormously fairer.

### Why 3 seconds?

Real-world race-to-race variance for the same competitor on similar wood is typically ±2–3 seconds. Sources:

- Wood grain variability (each block is different)
- Knots, inclusions, soft spots
- Technique wobble
- Equipment consistency (axe sharpness)
- Starting reflex

None of these scale with predicted time. A knot costs a beginner 2 seconds; it costs a world champion 2 seconds. Hence: **absolute**, and empirically **±3 seconds** captures observed variance well.

The number is also validated by Monte Carlo output — the `std_dev` field reported per competitor in the simulation stats tracks closely to 3.0s for predictions of typical confidence.

---

## What the simulation tracks

`run_monte_carlo_simulation()` runs between 500K (default for handicap validation) and 2M (default for championship simulator) race iterations. For each:

1. Draw a random perturbation `ε_i ~ Normal(0, 1.5)` for each competitor — [`variance.py`](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/variance.py)
2. Compute `actual_time_i = predicted_time_i + ε_i`
3. Compute finish time: `finish_i = mark_i + actual_time_i`
4. Rank competitors by finish time; record 1st/2nd/3rd

Across all simulations, STRATHMARK tracks:

| Metric | Description |
|---|---|
| `win_rate` | % of simulations this competitor won |
| `podium_rate` | % of simulations this competitor finished top-3 |
| `mean_finish_time` | Average finish time (validates mark arithmetic) |
| `std_dev_finish` | SD of finish time (validates ±3s model — should be ~3.0) |
| `min` / `max` | Range of observed finish times |
| `p25` / `p50` / `p75` | Percentile distribution |
| `consistency_rating` | Derived category based on std_dev |

### Consistency ratings

| std_dev | Rating | Interpretation |
|---|---|---|
| ≤ 2.5s | Very High | Very predictable |
| ≤ 3.0s | High | Matches ±3s model exactly |
| ≤ 3.5s | Moderate | Slightly above expected |
| > 3.5s | Low | Unusually variable — often a data issue |

Used primarily by the [Championship Simulator](Championship-Simulator) to surface "who's the wild card."

---

## Fairness grading

STRATHEX grades the handicap set by **win-rate spread** (highest win rate minus lowest):

| Spread | Grade | What it means |
|---|---|---|
| < 2% | Excellent | Essentially perfect — any competitor could win |
| < 4% | Very Good | Fair for any practical purpose |
| < 6% | Good | Minor bias; acceptable for most events |
| < 10% | Fair | Noticeable favorite — review marks |
| > 10% | Poor | Systematic bias — predictions are off |

Current STRATHEX performance in testing: **0.3s – 0.8s finish-time spread** translates to ~2–4% win-rate spread for balanced heats.

### What Poor means

A Poor grade means predictions are systematically biased for one or more competitors. Causes:

- Sparse history (the system blocks N<3 but N=3–5 is still thin)
- Competitor changed form recently (injury, training, equipment)
- Wood characteristics don't match history (quality misread)
- Cross-diameter scaling uncertainty (QAA tables are approximations)

Remedies:
- Re-examine the approval UI — are any predictions flagged with low confidence?
- Check wood quality rating
- Accept the bias and let the race decide (sometimes the prediction is just wrong)
- Manually override marks

---

## AI-assisted fairness narration

If Ollama is available, STRATHEX invokes `get_ai_assessment_of_handicaps()` after the Monte Carlo run. The LLM receives the win-rate distribution, per-competitor statistics, and selected prediction methods, then produces a narrative:

```
FAIRNESS ASSESSMENT — LLM

Rating: VERY GOOD (spread 2.8%)

The handicap set is well-balanced. Cody Labahn shows the highest win rate
(22.1%) driven by a slight ML under-prediction relative to his recent form;
this is within normal bounds for a 35-record training set. Eric Hoberg's
lower win rate (18.9%) traces to the QAA scaling from 325mm — scaled
predictions carry higher uncertainty and he may over-perform the prediction.

No systematic bias detected. Recommended: proceed without adjustments.
Consider manual +1 on Labahn if a closer race is desired.
```

The narrative is informational, not authoritative. The Handicapper still has final say ([AAA Rule 14](AAA-and-QAA-Rules-Compliance#rules-12-19--handicapping)).

If Ollama is unavailable, STRATHEX falls back to a purely statistical assessment (still useful, just less eloquent).

---

## When to run a simulation

| Situation | Run the simulation? |
|---|---|
| First tournament of the day | Yes — validates the prediction set before racing starts |
| After manual mark overrides | Yes — see how the overrides affected fairness |
| Generating semis/finals | Automatic — already embedded in the tournament flow |
| Championship Race Simulator (equal start) | Yes — 2M iterations, the whole point |
| Testing a new feature | Yes — regression check |
| Judges are confident in the predictions | Optional |

STRATHEX's default is to **always** run the simulation before the first race of an event. It takes under a second at 500K iterations and under 5 seconds at 2M. No reason to skip it.

---

## Implementation

STRATHMARK file: [`variance.py`](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/variance.py)

Key entry point:

```python
from strathmark.variance import run_monte_carlo_simulation

results = run_monte_carlo_simulation(
    handicap_results=mark_result_list,
    num_simulations=500_000,
    absolute_variance_std=1.5,  # 3-sigma = ±3s
)
```

Memory overhead:

| Competitors | Simulations | Memory |
|---|---|---|
| 4 | 2M | ~64 MB |
| 10 | 2M | ~160 MB |
| 4 | 500K | ~16 MB |

2M iterations on 10 competitors completes in 3–5 seconds on a modern laptop.

---

## Further reading

- [Championship Simulator](Championship-Simulator) — 2M-iteration equal-start predictor
- [Handicap System Explained § Stage 7](Handicap-System-Explained#stage-7--monte-carlo-fairness-validation)
- [STRATHMARK variance.py source](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/variance.py)
