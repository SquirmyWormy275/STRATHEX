---
title: np.polyfit crashes with DLASCLS/SVD errors on sparse or non-finite competitor data — guard with finite-value filter and point-count check
date: 2026-04-21
category: runtime-errors
module: predictions
problem_type: runtime_error
component: tooling
symptoms:
  - "'** On entry to DLASCLS parameter number 4 had an illegal value' traceback during ML training"
  - "'SVD did not converge' error during per-competitor trend calculation in ml_model.py"
  - "Training fails intermittently depending on which competitors are in the dataset"
  - "Works locally with a larger dataset, fails on smaller fixture / CI data"
root_cause: logic_error
resolution_type: code_fix
severity: medium
related_components:
  - database
tags: [numpy, polyfit, lstsq, lapack, sparse-data, ml-training, defensive-guards]
---

# np.polyfit crashes with DLASCLS/SVD errors on sparse or non-finite competitor data — guard with finite-value filter and point-count check

## Problem
In January 2026, ML training started crashing intermittently with LAPACK errors from deep inside `numpy.linalg.lstsq` (the backend for `np.polyfit`). The crash was `** On entry to DLASCLS parameter number 4 had an illegal value` and `SVD did not converge`. The offending call sites were per-competitor trend fitting — for each competitor, the code fit a linear trend through their historical times to capture skill trajectory as an ML feature.

The trigger was always the same shape: a competitor with one, zero, or only non-finite historical time values. `np.polyfit` with fewer than two finite points either crashes LAPACK directly or produces NaN coefficients that propagate silently into the feature vector.

## Symptoms
- ML training run fails with a traceback through `numpy.linalg.lstsq` → `gelsd` → `DLASCLS`
- Error varies depending on exact input: sometimes `SVD did not converge`, sometimes `illegal value in parameter number 4`
- Fails on fresh checkouts where `woodchopping.xlsx` has been filtered to a smaller test subset
- Reproduces for competitors whose historical record has been imported but whose `Time` values contain NaN or strings-that-coerce-to-NaN
- Features look fine when inspected casually; the failure is inside the training function

## What Didn't Work
- Wrapping the whole training function in a bare `try/except`. Catches the crash but leaves every affected competitor with NaN features, which propagates into the model and produces garbage predictions
- Bumping numpy or scipy versions. The DLASCLS error is LAPACK's correct behavior on malformed input — the problem is in what we hand it, not which version of numpy is shipped
- Pre-coercing the time column with `pd.to_numeric(errors="coerce")`. This converts non-numeric strings to NaN (correct) but doesn't drop them before polyfit sees them — the NaN makes it to LAPACK

## Solution
**Defensive guard upstream of `np.polyfit`**, applied in both [woodchopping/data/preprocessing.py](../../../woodchopping/data/preprocessing.py) and [woodchopping/predictions/ml_model.py](../../../woodchopping/predictions/ml_model.py):

```python
import numpy as np

def safe_linear_trend(x: np.ndarray, y: np.ndarray, default: float = 0.0) -> float:
    """Fit a linear trend, returning `default` for sparse or degenerate input.

    Returns the slope (first coefficient of polyfit degree=1) so downstream
    features get a scalar 'trend' value per competitor.
    """
    mask = np.isfinite(x) & np.isfinite(y)
    x_clean = x[mask]
    y_clean = y[mask]

    if len(x_clean) < 2:
        return default

    try:
        slope, _intercept = np.polyfit(x_clean, y_clean, deg=1)
        return float(slope) if np.isfinite(slope) else default
    except np.linalg.LinAlgError:
        return default
```

Key parts:

1. **Finite-value filter first.** Any NaN / inf in either array is dropped before fitting. This is the most common failure source.
2. **Point-count check second.** After filtering, if fewer than two finite points remain, return the default (0.0 = "no trend information") without calling polyfit at all. A 2-point fit is already suspect, but it won't crash LAPACK.
3. **Catch `LinAlgError` last.** Belt-and-braces for the rare case where two or more finite points still produce a degenerate matrix (e.g., all x-values identical).
4. **Return a scalar default**, not NaN. NaN propagates through feature engineering and ends up in the ML input vector; a concrete 0.0 is an honest "we don't have enough data to estimate a trend" signal.

## Why This Works
`np.polyfit` delegates to `np.linalg.lstsq`, which calls LAPACK's `gelsd` / `DLASCLS` routines. LAPACK's input validation asserts on dimensions, finite-ness, and rank — hitting any of these with bad input produces an error that reads like an internal bug because it comes from deep in the FORTRAN code. The fix is always to validate input before LAPACK sees it.

Returning a default (0.0 slope) for competitors with insufficient data is defensible for a trend feature specifically: "no trend information available" is a legitimate value, not a gap. For other features — say, a career-average feature — the right default might be the event mean, not zero. **Choose the default to match the semantic of the feature, not the shape of the math.**

## Prevention
- Any new feature engineering that calls `np.polyfit`, `np.linalg.lstsq`, or `scipy.optimize.curve_fit` must filter to finite values and check the remaining point count before fitting. This is mandatory, not optional
- Wrap linear algebra calls in `try/except np.linalg.LinAlgError` at the feature level, with a defaulted return. Never let a LinAlgError reach the training loop
- When data preprocessing is updated (new columns, new import source), re-audit the feature engineering functions. Preprocessing and feature engineering are tightly coupled — a change in one can break the other silently
- ML training tests must include a "sparse competitor" fixture (one competitor with zero valid times, one with one, one with non-finite-only). Unit tests that only run on the full production dataset will miss these cases until a CI run or fresh checkout triggers them
- When converting a Time column from Excel, be explicit: `pd.to_numeric(..., errors="coerce")` then `.dropna()` before handing off. Do not assume the string-to-float conversion has removed bad rows — it produces NaN, which is still bad for polyfit

## Related Issues
- [woodchopping/data/preprocessing.py](../../../woodchopping/data/preprocessing.py) — primary guard location
- [woodchopping/predictions/ml_model.py](../../../woodchopping/predictions/ml_model.py) — per-competitor trend calculation
- [docs/ML_AUDIT_REPORT.md](../../ML_AUDIT_REPORT.md) — ML feature set documentation
- Python numpy docs: `numpy.polyfit`, `numpy.linalg.lstsq` — LAPACK backend notes
