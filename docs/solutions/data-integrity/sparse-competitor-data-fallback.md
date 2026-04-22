---
title: Competitors with no event history must be excluded from the pool — shrinkage toward event mean made sparse competitors look competitive
date: 2026-04-21
category: data-integrity
module: predictions
problem_type: logic_error
component: database
symptoms:
  - "Norah Steed (no SB history) predicted to rank ahead of Tristan VanBeek and Stirling Hart (established competitors with many SB results)"
  - "Blank-record competitors got predictions pulled toward the event mean, which is dominated by fast times"
  - "No crash, no warning — the broken ranking only became visible when a judge noticed the ordering was impossible"
root_cause: logic_error
resolution_type: code_fix
severity: high
related_components:
  - assistant
tags: [data-sparsity, competitor-eligibility, shrinkage, cascading-fallback, prediction-accuracy]
---

# Competitors with no event history must be excluded from the pool — shrinkage toward event mean made sparse competitors look competitive

## Problem
In January 2026, a handicap calculation for a Standing Block event ranked Norah Steed (no SB history in the dataset) ahead of Tristan VanBeek and Stirling Hart — both established US competitors with many SB results. The system was doing exactly what it was designed to do: when a competitor had no data, the baseline fell back to the event mean. But the event mean is dominated by competitive times, so a blank record ended up looking "average" — which, in a field of strong competitors, still ranks high.

## Symptoms
- Unknown or historically sparse competitor outranks well-documented strong competitors
- No error, no warning in logs — the prediction cascade worked as specified
- Ordering that a knowledgeable judge would immediately identify as impossible (e.g., a competitor with zero SB results ranked among the top 5)
- The fairness Monte Carlo showed the expected spread, because the issue wasn't variance — it was systematic bias in the point estimate

## What Didn't Work
- Trusting the cascading fallback alone. The cascade is correct as a defensive mechanism, but without an eligibility filter upstream it produces absurd rankings
- Adding a warning but keeping the competitor in the pool. Judges under time pressure in a live tournament will not stop to evaluate a warning — they'll trust the ordering
- Treating the problem as "needs more historical data." The dataset will always have new competitors. The system must handle this case explicitly, not wait for it to go away

## Solution
**Two-layer defense**: eligibility filter at the pool-building step, plus cascading fallback within the predictor for the competitors that pass the filter.

### 1. Eligibility filter (new)
Before handicap calculation, filter the competitor pool to only include competitors with enough event-specific data:

```
For each selected competitor:
  Count historical results for the current event (SB / UH)
  If count < minimum_required (currently 3):
    Exclude from the handicap calculation
    Offer the judge an on-the-spot data entry path
    Or skip the competitor for this event
```

The judge sees a clear "competitor X has no history in this event — enter times now or skip?" dialog. No silent fallbacks.

### 2. Cascading fallback (existing, unchanged)
For competitors who *do* pass the eligibility filter, the predictor still falls back through three levels when exact data is unavailable:

```
Level 1: Exact match  — competitor + species + event
Level 2: Looser match — competitor + event (any species)
Level 3: Event baseline — all competitors, that event
```

This handles the common case of a competitor who has SB history but not on this specific species — the fallback uses their event-level baseline. It is *not* the layer that should be handling "no history at all".

## Why This Works
Shrinkage toward the event mean is a reasonable prior *only when the estimator has some data to be pulled toward the mean*. With zero data, "shrinkage to the mean" is just "assume average" — and in a pool of strong competitors, assuming average means outranking the bottom half of the field.

The eligibility filter establishes a minimum-information threshold. Below it, the competitor is not a candidate for handicap calculation at all. Above it, the cascading fallback handles the normal data-sparsity cases where the competitor has *some* relevant history but not a perfect match.

Separating these two concerns — "is this competitor eligible" vs. "what do we do with the data they have" — is what makes the system both robust and explainable. A judge can defend the handicap calculation at a competition because every competitor in the pool has demonstrable event-specific history.

## Prevention
- The minimum-data threshold (3 records) should never be lowered without explicit tournament-rules review. Lower thresholds produce the Norah Steed failure mode
- When adding a new event type (e.g., 3-Board Jigger), decide the eligibility threshold *before* the event goes live. If historical data is thin across the board, the event may need a manual-mark mode until a baseline accumulates
- The data-entry-on-the-spot path must remain fast — a judge with 10 minutes before a heat will not manually enter 3 historical times per new competitor. Consider a "minimum viable" 3-time template to speed this up
- Any refactor of the baseline or prediction cascade must preserve the eligibility filter. It is upstream of the cascade for a reason
- When testing prediction accuracy, include "sparse competitor" cases in the fixture. The fairness Monte Carlo does not exercise this path — unit tests must
- Audit the roster periodically: competitors with persistent empty SB or UH records are unlikely to become active and can be soft-archived from the selection pool to reduce clutter

## Related Issues
- [CLAUDE.md](../../../CLAUDE.md) — "Minimum 3 historical times required for new competitors"
- [CLAUDE.md "Cascading Fallback Logic for Predictions"](../../../CLAUDE.md) — describes the 3-level fallback for competitors who pass the eligibility filter
- [wiki/Data-Model.md](../../../wiki/Data-Model.md) — data requirements, judge-facing
- [woodchopping/predictions/baseline.py](../../../woodchopping/predictions/baseline.py) — `get_competitor_historical_times_flexible()` and `get_event_baseline_flexible()`
- [woodchopping/ui/competitor_ui.py](../../../woodchopping/ui/competitor_ui.py) — eligibility UI
