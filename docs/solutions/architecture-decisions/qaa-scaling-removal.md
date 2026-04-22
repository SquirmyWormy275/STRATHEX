---
title: QAA tables were purged from the time-prediction path because they inverted the diameter-time relationship
date: 2026-04-21
category: architecture-decisions
module: predictions
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Adding or modifying diameter scaling logic
  - Considering reintroducing QAA tables for prediction
  - Debugging why larger-diameter predictions look faster than smaller-diameter ones
  - Adding new prediction methods that need diameter normalization
related_components:
  - documentation
tags: [qaa, diameter-scaling, predictions, monotonicity, v6, engineering-judgment]
---

# QAA tables were purged from the time-prediction path because they inverted the diameter-time relationship

## Context
On 2026-03-09 (V6.0 / commit `e9dff99` "QAA purge") three files were deleted in a single sweep: `woodchopping/predictions/qaa_scaling.py` (568 lines), `woodchopping/predictions/qaa_legacy.py` (119 lines), and `tests/test_qaa_interpolation.py` (178 lines). Every reference to QAA tables in the prediction pipeline was removed. The replacement is a calibrated power-law diameter scaling derived from the actual competition data.

QAA tables are still referenced in the codebase and in the wiki — but only for their legitimate use: AAA / QAA compliance checks (mark floor of 3s, mark ceiling of 180s, eligibility rules). The tables are gone from the prediction path. Future agents who see "QAA" in AAA rule docs should not conclude they should reintroduce the tables for time prediction.

## Guidance
**Do not reintroduce QAA mark tables into the time-prediction path.** QAA tables are designed for handicap-mark assignment, which has the opposite shape from time prediction:

| Aspect | QAA mark table | Time prediction |
| --- | --- | --- |
| Domain | Diameter → mark | Diameter → time |
| Monotonicity | Bigger block → smaller mark (less head start) | Bigger block → longer time |
| Sign of diameter coefficient | Negative | Positive |
| Intended use | Hand-computing handicaps without a predictor | Normalizing historical times to a reference diameter |

Using a decreasing-in-diameter function (marks) to normalize time (which increases in diameter) flips the sign. The system was predicting that 325mm blocks would be chopped faster than 300mm blocks — physically wrong. A January 2026 audit found 35 of 92 competitor-event pairs showed monotonicity violations: the scaled prediction decreased as diameter increased.

**The replacement is calibrated power-law scaling from empirical data:**

```python
# Not the actual code — conceptual pattern
# time_at_reference = observed_time * (reference_diameter / observed_diameter) ** alpha
# alpha is calibrated from the actual STRATHEX dataset, not from QAA tables
```

This is owned by STRATHMARK (after the V6.0 extraction). See [strathmark_adapter.py](../../../woodchopping/strathmark_adapter.py).

## Why This Matters
QAA tables are "institutional knowledge" from 150+ years of Australian woodchopping handicapping, which makes them tempting to reuse wherever diameters and times appear. That temptation is the failure mode this doc exists to prevent.

**Concrete impact of the pre-purge bug:**

- Silent wrong-direction scaling. No crash, no error message — just systematically biased predictions
- Competitors choosing a larger block in the hope of a "faster" scaled time were getting a marginally better predicted finish (the opposite of physical reality)
- Monte Carlo fairness validation showed the expected spread, which masked the underlying direction error — the bias was consistent across all competitors, so the spread was normal
- The bug survived until a diameter-monotonicity audit explicitly compared predicted times at adjacent diameter bins

**Why power-law from our own data works:** STRATHEX/STRATHMARK has a competition dataset where time-vs-diameter is directly observable for the same competitor/species/event combinations. Fitting `alpha` from that dataset is the right-shaped function in the right direction, calibrated for the competitors and wood actually in the system. QAA tables were calibrated for a different country's axemen on different wood decades ago — there was no reason to expect the shape to transfer even if the direction had been correct.

## When to Apply
- Anyone considering "why don't we use the QAA diameter tables for X?" — the answer is always "because QAA tables are marks-shaped, not time-shaped"
- Anyone debugging a prediction where bigger blocks look faster than smaller ones — check for sign-inverted scaling first
- Anyone adding a new scaling factor (age, wood species, competitor skill) — verify monotonicity by plotting predicted time vs. the scaling variable before shipping

## Examples

**What the direction-inversion looked like in practice** (reconstructed from session history):

```
Competitor: Matt Cogar
Event: Standing Block
Historical record: 28.5s on 300mm

QAA-scaled prediction for 325mm: 27.8s  ← WRONG (should be slower, not faster)
Power-law prediction for 325mm:  30.2s  ← Correct direction
```

**Monotonicity audit pattern** (apply to any new scaling):

```python
# For each competitor with multiple diameter records in the same event,
# sort by diameter and check that predicted time is non-decreasing.
for (comp_id, event), group in df.groupby(["CompetitorID", "Event"]):
    sorted_group = group.sort_values("Diameter")
    predicted = sorted_group["PredictedTime"].values
    if not all(predicted[i] <= predicted[i+1] for i in range(len(predicted)-1)):
        print(f"Monotonicity violation: {comp_id} in {event}")
```

## Related
- [CLAUDE.md](../../../CLAUDE.md) — no longer references QAA in the prediction path
- [wiki/Prediction-Methods.md](../../../wiki/Prediction-Methods.md) — describes the current power-law approach
- [wiki/AAA-and-QAA-Rules-Compliance.md](../../../wiki/AAA-and-QAA-Rules-Compliance.md) — QAA's legitimate use (rule compliance), not prediction
- [docs/QAA_INTERPOLATION_IMPLEMENTATION.md](../../QAA_INTERPOLATION_IMPLEMENTATION.md) — historical doc from the pre-purge era. Treat as archival, not current behavior
- Commit `e9dff99` — the purge itself
- Commit `371406a` — V6.0 extraction in the same cycle
