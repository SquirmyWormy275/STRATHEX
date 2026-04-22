---
title: STRATHMARK was extracted from STRATHEX in V6.0 because two distinct buyer types exist
date: 2026-04-21
category: architecture-decisions
module: packaging
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Adding new handicap-calculation features — decide which repo owns them
  - Considering reimplementing calculation logic inside STRATHEX
  - Designing new integrations (Missoula Pro-Am Manager, future clients)
  - Evaluating whether a change should live in the adapter or in the engine
related_components:
  - development_workflow
  - documentation
tags: [strathmark, architecture, adapter-pattern, v6, packaging, extraction]
---

# STRATHMARK was extracted from STRATHEX in V6.0 because two distinct buyer types exist

## Context
In V6.0 (commit `371406a` on 2026-03-09) all handicap calculation, Monte Carlo simulation, prediction aggregation, and AI fairness assessment moved out of STRATHEX into STRATHMARK — a separate pip-installable package at [github.com/SquirmyWormy275/STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK). STRATHEX kept only the tournament-management surface: CLI UI, Excel I/O, multi-round/multi-event flows, payouts, championship simulator. The bridge between the two repos is [woodchopping/strathmark_adapter.py](../../../woodchopping/strathmark_adapter.py) — the only file in STRATHEX that imports from `strathmark`.

This was not a refactor for its own sake. It was a business-driven architectural split surfaced during a March 2026 CEO-review session. Without understanding the rationale, future agents will either (a) reimplement calculation logic inside STRATHEX, duplicating STRATHMARK's work, or (b) fight the adapter pattern when adding features.

## Guidance
**Two distinct buyer types justify the separation:**

1. **Event organizers** — use STRATHEX directly as a standalone CLI tool. Retro aesthetic is intentional; they want a Windows-native Python app that runs on modest hardware and reads an Excel file. No integration work required.
2. **Developer integrators** — build their own tournament-management systems and want only the calculation engine. STRATHMARK as a pip package serves this need. The first real integration was the Missoula Pro-Am Manager repo (April 2026).

**Where each concern lives:**

| Concern | STRATHEX | STRATHMARK |
| --- | --- | --- |
| Tournament menu, CLI, Excel sheets | ✓ | — |
| Multi-round & multi-event workflow | ✓ | — |
| Competitor roster, wood config, payouts, championship simulator | ✓ | — |
| Handicap mark calculation | — | ✓ |
| Monte Carlo simulation (±3s variance) | — | ✓ |
| Prediction cascade (baseline, ML, LLM, confidence scoring) | — | ✓ |
| Persistent result history (SQLite, Supabase) | — | ✓ |
| Prompt library for AI reasoning | — | ✓ |

**Decision rules for future changes:**

- A change to how marks are computed → STRATHMARK
- A change to how the UI shows marks → STRATHEX
- A new prediction feature → STRATHMARK (and prompts updated per the LLM-prompt-maintenance standing order)
- A new event type or workflow → STRATHEX (with thin calls into STRATHMARK if it needs calculation)
- A new Excel column → STRATHEX, with dual-write to `ResultStore` via [store_registry.py](../../../woodchopping/data/store_registry.py)

**Adapter pattern as the only integration point:** `strathmark_adapter.py` is the only file in STRATHEX allowed to `import strathmark`. Everything else calls through the adapter. This keeps the blast radius of STRATHMARK API changes bounded to one file and prevents accidental coupling. If you find yourself wanting to `import strathmark` somewhere else, add a method to the adapter instead.

## Why This Matters
- **Without the split**: a developer building a tournament manager would have to vendor all of STRATHEX's CLI, UI, and Excel code just to get handicap math. That's a non-starter for any serious integration.
- **Without the adapter discipline**: every STRATHEX file that touched calculation would break when STRATHMARK rev'd its API. The adapter absorbs the impact.
- **Without documenting the rationale**: agents will re-add calculation logic inside STRATHEX when they need a tweak, because calling through the adapter feels like indirection. Over time this creates drift — STRATHEX's copy will diverge from STRATHMARK's authoritative version, and judges will see different marks from different entry points.
- The `v5.2-legacy` branch preserves the pre-split monolithic version for anyone who genuinely cannot install STRATHMARK. It is explicitly not maintained going forward.

## When to Apply
- Any change that touches `woodchopping/handicaps/`, `woodchopping/simulation/`, or the prediction cascade — check whether the change belongs upstream in STRATHMARK first
- Any integration attempt — consume STRATHMARK, not STRATHEX
- Any question of the form "should I just put this directly in X module?" — the answer is almost always "add it to the adapter and let STRATHMARK own the real logic"

## Examples

**Correct pattern — new field flows through the adapter:**

```python
# woodchopping/strathmark_adapter.py
def calculate_handicaps_with_tournament_context(
    competitors_df: pd.DataFrame,
    wood_profile: WoodProfile,
    tournament_results: dict[str, float] | None = None,
) -> list[HandicapResult]:
    records = [_df_row_to_competitor_record(row) for _, row in competitors_df.iterrows()]
    return strathmark.HandicapCalculator().calculate(
        records, wood_profile, tournament_results=tournament_results
    )

# woodchopping/ui/handicap_ui.py — calls through the adapter, never imports strathmark directly
from woodchopping.strathmark_adapter import calculate_handicaps_with_tournament_context
```

**Anti-pattern — UI code reaching into the engine:**

```python
# woodchopping/ui/tournament_ui.py — WRONG
import strathmark  # This file should not exist
marks = strathmark.HandicapCalculator().calculate(...)
```

## Related
- [CLAUDE.md](../../../CLAUDE.md) — V6.0 architecture block at the top of the file
- [woodchopping/strathmark_adapter.py](../../../woodchopping/strathmark_adapter.py) — the only STRATHEX file importing `strathmark`
- [wiki/Architecture.md](../../../wiki/Architecture.md) — judge-facing explanation of the split
- [wiki/Ecosystem.md](../../../wiki/Ecosystem.md) — describes both repos and their relationship
- STRATHMARK repo: `https://github.com/SquirmyWormy275/STRATHMARK`
- Commit `371406a` — V6.0 extraction
- Commit `d26e958` — refactor cleanup immediately after extraction
- `v5.2-legacy` branch — preserved pre-split snapshot (unmaintained)
