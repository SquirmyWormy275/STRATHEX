---
title: ML trained on 19 features but inference built only 7 — silent fall-through meant ML was never contributing to handicaps
date: 2026-04-21
category: test-failures
module: predictions
problem_type: test_failure
component: tooling
symptoms:
  - "ML prediction column showed N/A for every competitor in the prediction comparison table"
  - "Handicap calculations used only Baseline or LLM — never ML"
  - "No crash, no error log — `predict_time_ml()` silently returned None for every call"
  - "Training succeeded and reported good metrics (MAE 2.55s for SB, 2.35s for UH), so the training side looked healthy"
root_cause: logic_error
resolution_type: test_fix
severity: high
related_components:
  - development_workflow
tags: [xgboost, ml, feature-count, silent-failure, end-to-end-testing, ai-slop]
---

# ML trained on 19 features but inference built only 7 — silent fall-through meant ML was never contributing to handicaps

## Problem
In January 2026, an audit revealed that the XGBoost prediction column in the handicap results table had been empty for an unknown length of time. Every competitor's ML prediction was `N/A`. The training code was building feature vectors with 19 features (competitor_avg, event_encoded, size_mm, six wood properties, experience, trend, variance, median_diameter, recency, career_phase, month seasonality, and interaction terms). The inference code in `predict_time_ml()` was only constructing a 7-feature vector.

When XGBoost received a feature vector of the wrong length, the call returned None — either because the XGBoost internal validation rejected the input silently, or because a bare `except Exception: return None` further up the call stack swallowed the exception. The predictor selection logic then fell through to LLM or Baseline, producing handicaps that looked reasonable and a fairness Monte Carlo that passed — masking the fact that ML was inert.

The user's reaction when it was discovered: *"What the fuck kind of AI slop mismatch was that lol. Train it on 19 and implement 7 lol."*

## Symptoms
- Prediction comparison table shows ML as `N/A` across every row
- `predict_time_ml()` returns `None` even though the model trained successfully
- No exception is ever logged — the failure is entirely silent
- Selected predictions come exclusively from Baseline or LLM
- No degradation in fairness Monte Carlo metrics, because the fallback predictions are themselves reasonable
- The bug persists across many sessions before anyone notices, because ML was expected to be "just one contributor among several"

## What Didn't Work
- Looking at training logs. Training reported clean MAE numbers, which made the ML side look fine. The failure was downstream, in inference
- Adding more logging around the predictor selection logic. The fallback was intentional behavior (that's what cascading fallback is *for*); the logs said "selected Baseline" as designed. Nothing indicated a mismatch
- Trying to debug `predict_time_ml()` in isolation. Without a real feature-building call, the inner failure mode (shape mismatch to a 19-feature model) didn't reproduce — the feature builder itself was the bug, not the XGBoost call

## Solution
**Three changes, applied together:**

### 1. Rebuild `predict_time_ml()` to construct the full 19-feature vector at inference time
The fix is mechanical — every feature used at training time must be computed at inference time from the live inputs (competitor, event, wood profile, and competitor history DataFrame). The authoritative feature list lives in [woodchopping/predictions/ml_model.py::get_ml_features()](../../../woodchopping/predictions/ml_model.py). `predict_time_ml()` must call that same function (or a shared helper) so drift between training and inference is impossible going forward.

### 2. Add a shape assertion at the XGBoost call boundary
```python
# woodchopping/predictions/ml_model.py
expected_features = model.feature_names_in_.tolist()  # Or stored on the model wrapper
feature_vector = build_feature_vector(competitor, event, wood, history)
if list(feature_vector.columns) != expected_features:
    raise ValueError(
        f"Feature mismatch: model expects {expected_features}, "
        f"got {list(feature_vector.columns)}"
    )
```

Failing loudly at the call site is the right move. The old silent-None return was an anti-pattern — it hid the bug behind a fallback that looked reasonable.

### 3. Add an end-to-end ML-activation test
The original bug was invisible to unit tests. Add a test that:

- Loads a realistic competitor/event fixture
- Runs the full prediction aggregator
- Asserts that the ML prediction is **not** None and **is** selected by confidence scoring for at least some rows

Without this test, the regression will recur the next time feature engineering drifts. See [tests/conftest.py](../../../tests/conftest.py) for the current test collection rules — this test should live with the integration tests, not as an isolated `predict_time_ml` unit test.

## Why This Works
The underlying failure is a *training/inference contract* problem: two functions must agree on the feature list, but the codebase didn't enforce the agreement. The three fixes each target a different failure mode:

- Shared feature-list source (1) prevents the mismatch from happening
- Shape assertion at the boundary (2) makes the mismatch crash loudly if it ever happens again
- End-to-end test (3) catches the whole regression even if the assertion is bypassed or the feature list drifts in a way that matches the count but not the semantics

**Silent fallbacks are the dangerous part.** A try/except that returns None on failure sounds defensive, but it converts a loud bug into a silent degradation. For prediction code, the right default is almost never "return None and hope the caller has a fallback" — it's "raise, log the failure, and let the caller decide."

## Prevention
- Any change to feature engineering must update training *and* inference in the same commit. Use a single shared `build_feature_vector(...)` function called from both paths. If it's inconvenient to share, that is the smell — fix the structure
- XGBoost model objects in this repo should persist their feature names (`feature_names_in_` or an explicit wrapper field). Inference should look up the expected features from the model, not hardcode them
- No silent `except Exception: return None` in prediction code. If a predictor fails, raise — the aggregator can decide whether to catch and fall through
- End-to-end ML-activation test must be part of the standard CI run (it is not Ollama-dependent, so no `-m "not ollama"` exclusion applies). The test should assert ML was selected for at least some fraction of a fixture set
- When retraining the model, re-run the end-to-end test against the new artifact before shipping. Do not trust training metrics alone as evidence that inference works

## Related Issues
- [woodchopping/predictions/ml_model.py](../../../woodchopping/predictions/ml_model.py) — `get_ml_features()` (feature list source), `train_xgboost_model()`, `predict_time_ml()`
- [woodchopping/predictions/prediction_aggregator.py](../../../woodchopping/predictions/prediction_aggregator.py) — the selection logic that hid the failure
- [docs/ML_AUDIT_REPORT.md](../../ML_AUDIT_REPORT.md) — current feature set documentation
- [docs/solutions/data-integrity/sparse-competitor-data-fallback.md](../data-integrity/sparse-competitor-data-fallback.md) — related sparsity-handling pattern; the eligibility filter feeds the ML training set
