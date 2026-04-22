---
title: Wood quality is 1=softest, 10=hardest — historical data predates this convention and is all recorded as 5
date: 2026-04-21
category: data-integrity
module: data
problem_type: logic_error
component: database
symptoms:
  - UI described quality as "higher = firmer" but code treated higher as softer, inverting every quality adjustment
  - All 998 rows of pre-existing historical data had Quality = 5 regardless of the actual wood on the day
  - LLM prompts, ML features, and baseline normalization all had to be re-aligned to the correct sign
root_cause: logic_error
resolution_type: code_fix
severity: high
related_components:
  - assistant
  - email_processing
tags: [wood-quality, data-model, historical-data, prediction, sign-inversion]
---

# Wood quality is 1=softest, 10=hardest — historical data predates this convention and is all recorded as 5

## Problem
Two related issues surfaced in January 2026 while auditing baseline accuracy:

1. **Sign inversion.** The UI described wood quality as "1 = soft, 10 = hard" but parts of the prediction stack (baseline normalization, LLM prompts, ML feature engineering) treated higher quality as *easier* wood. Every quality adjustment was running the wrong direction. A rating of 8 (above-average firmness) was biasing predictions *faster* when it should have been biasing them slower.
2. **Historical data is uninformative.** Every row in `woodchopping.xlsx` that predates this system has `Quality = 5`. Woodchopping/timbersports did not record wood quality before STRATHEX started demanding it. The quality field is a *forward-looking* signal — it only carries information for competitions scored inside this system.

## Symptoms
- Predictions on hard wood (quality 8–10) came back faster than historical baseline — physically wrong
- LLM quality-adjustment reasoning described hardness correctly in text but applied it the wrong way numerically
- ML models trained on the historical dataset gave near-zero weight to the quality feature (all 998 rows had the same value, so the feature carried no variance)
- Normalization code that adjusted "to neutral quality 5" was effectively a no-op on historical data but flipped the wrong way on fresh data

## What Didn't Work
- Rewording the UI prompt ("hard = 10" vs "firm = 10") without also fixing the code. Cosmetic; leaves the sign error in place
- Adding a second "hardness" field alongside quality. Creates a schema bifurcation and leaves the sign error hidden under a rename

## Solution
**Standardize on 1 = softest, 10 = hardest across the entire stack** (code, prompts, UI, docs). The authoritative definition is documented in [CLAUDE.md "Wood Quality Scale"](../../../CLAUDE.md):

```
0-3:  Soft/rotten wood   (faster times)
4-7:  Average firmness for species
8-10: Above average firmness (slower times)
```

Every quality adjustment must bias predictions *slower* as quality rises. In the baseline, LLM prompts, and ML features, this is enforced by:

- Baseline normalization — multiplier increases with quality
- LLM prompt — explicit statement that "higher quality = harder wood = slower predicted time"
- ML feature — the raw quality value feeds in directly with a monotone-increasing constraint (XGBoost `monotone_constraints`)

**Handle the historical-data constraint separately:** treat `Quality = 5` in pre-system data as "unknown / assume average" rather than "actual neutral". In practice this means the quality feature contributes near-zero signal for historical rows and only starts carrying information once the system has logged tournaments under the new convention. Do not backfill old rows with guessed quality values; the guess is noise, not signal.

## Why This Works
**Why the sign matters:** predictions flow into handicaps, and handicaps translate directly into mark offsets that determine who starts when. A sign-inverted quality adjustment doesn't just make predictions wrong — it systematically advantages competitors on hard wood and penalizes them on soft wood (or vice versa, depending on whose prediction drives the mark). The fairness invariant ("absolute ±3s across all competitors") holds only if the prediction itself is unbiased.

**Why the historical constraint matters:** a future maintainer looking at `woodchopping.xlsx` might notice that quality is always 5 and assume the system is broken. It isn't. The Excel file was populated from prior competition records that never tracked this field. The forward-looking rows will carry real quality values. Any backfill attempt should be rejected.

## Prevention
- Any new code that reads `Quality` must explicitly state the convention in a comment or docstring. Never assume a reader knows which end is "soft"
- Every LLM prompt that mentions quality must state the direction in the prompt body. The LLM cannot infer convention from variable names
- ML models must use monotone constraints on the quality feature (`monotone_constraints = {"quality": 1}`). This gives the model a direction and catches accidental sign flips during training
- Before shipping any quality-related change, run a sanity check: increase quality from 5 to 8 on a fixed competitor/event/diameter, verify the predicted time goes *up*
- Never backfill `Quality` in historical rows. If a row's actual wood quality is unknown, leave it at 5 (the "unknown / assume average" value). Quality only carries information going forward
- New dataset entries must record actual quality at the time of competition. The judge's quality assessment is the ground-truth signal — without it, future ML features will never learn the relationship

## Related Issues
- [CLAUDE.md "Wood Quality Scale"](../../../CLAUDE.md) — canonical definition
- [wiki/Data-Model.md](../../../wiki/Data-Model.md) — judge-facing description of the Results sheet
- [woodchopping/predictions/ai_predictor.py](../../../woodchopping/predictions/ai_predictor.py) — LLM prompt that must keep the direction explicit
- [woodchopping/predictions/baseline.py](../../../woodchopping/predictions/baseline.py) — baseline normalization using quality
- [woodchopping/predictions/ml_model.py](../../../woodchopping/predictions/ml_model.py) — ML feature engineering with monotone constraints
