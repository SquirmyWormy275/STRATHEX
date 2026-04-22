---
title: When a system feature ships, every LLM prompt that reasons about that feature must ship updated in the same commit
date: 2026-04-21
category: best-practices
module: predictions
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Adding any new prediction feature (tournament weighting, new baseline method, new scaling factor)
  - Changing prediction methodology (time-decay, ML features, confidence scoring)
  - Adding optional parameters that affect model reasoning
  - Fixing a prediction bug where the LLM needs different handling
related_components:
  - documentation
  - development_workflow
tags: [llm, prompts, feature-parity, tournament-weighting, development-discipline]
---

# When a system feature ships, every LLM prompt that reasons about that feature must ship updated in the same commit

## Context
STRATHEX uses LLM prompts in three critical places: time prediction (baseline quality adjustment), fairness assessment (Monte Carlo result analysis), and championship race commentary. Each prompt describes to the LLM what the system is doing so the LLM can reason correctly. When a system feature changes but its prompts are not updated, the LLM keeps reasoning against the old system — silently producing wrong adjustments, double-counting corrections, or missing opportunities that the new feature unlocks.

This failure mode has already cost the project weeks of debugging. V4.4 added tournament result weighting (97% same-tournament / 3% historical) to the baseline, but the LLM prompts still described the baseline as a simple average. The LLM dutifully applied its "quality adjustment" on top of an already-tournament-weighted baseline — double-adjusting in a way that was invisible from the output (the numbers looked plausible) but systematically wrong. The fix landed in the January 12, 2026 [PROMPT_CHANGELOG.md](../../PROMPT_CHANGELOG.md) as "time_prediction v2.0."

## Guidance
**Feature parity is a shipping rule, not a nice-to-have.** The rule has three layers:

### 1. Every feature change maps to at least one prompt update
If a change affects how a prediction is computed, at least one of the three prompt sites is affected:

- `woodchopping/predictions/ai_predictor.py::predict_competitor_time_with_ai()` — applies a quality adjustment on top of the baseline. Any change to what the baseline does, how time-decay works, or how tournament data flows in must update this prompt
- `woodchopping/simulation/fairness.py::get_ai_assessment_of_handicaps()` — analyzes Monte Carlo fairness results. Any change to variance, confidence scoring, or the handicap calculation itself must update this prompt
- `woodchopping/simulation/fairness.py::get_championship_race_analysis()` — commentary on championship-race predictions. Any change to what the championship simulator surfaces must update this prompt

### 2. Updates ship in the same commit as the feature
Not "in the next release," not "before the demo" — in the same commit. The standing order in [CLAUDE.md "LLM PROMPT MAINTENANCE"](../../../CLAUDE.md) makes this explicit. Reviews should block on it.

### 3. Updates follow the checklist
From CLAUDE.md, repeated here because the failure modes are real:

- [ ] **Identify affected prompts** — which of the three sites reason about this feature?
- [ ] **Add system context** — one paragraph explaining the new capability to the LLM, in plain language
- [ ] **Add conditional sections** — if the feature is optional, tell the LLM explicitly when it applies and when to ignore it
- [ ] **Update examples** — any example values, test cases, or scenarios in the prompt must reflect the new behavior
- [ ] **Test thoroughly** — compare before/after predictions on a fixture set. A prompt update that doesn't change predictions is either wrong or unnecessary
- [ ] **Log in PROMPT_CHANGELOG.md** — version the prompt (e.g., `time_prediction v2.1`), record what changed, why, and when

## Why This Matters
**The LLM cannot infer what the system does.** It can only reason about what the prompt tells it. When the system does one thing and the prompt describes another, the LLM produces output that is internally consistent but externally wrong — exactly the hardest kind of bug to catch.

**Concrete V4.4 failure:** tournament weighting was added to the baseline so that heats/semis/finals use same-wood data at 97% weight. The baseline prediction passed to the LLM was already tournament-weighted. The LLM prompt, unchanged since V4.3, still said "here is a baseline from historical data; adjust for wood quality." The LLM applied a multiplicative quality adjustment on top — but the baseline was *already* incorporating quality-relevant information from the tournament's own runs. Result: a systematic over-adjustment in the direction of whatever the LLM inferred about the wood. The mark calculations still looked reasonable; the Monte Carlo still showed the expected spread; nobody noticed until someone audited prediction accuracy against actual recorded heat times and found the LLM was systematically over-correcting.

**Concrete lesson:** the cost of catching this failure in a prompt review (15 minutes per feature) is orders of magnitude smaller than the cost of catching it in a post-tournament audit (weeks of debugging, loss of judge trust, and "we'll fix it for next season").

**Why the prompts can't be auto-generated:** prompts are not documentation. They are part of the inference pipeline. A generated prompt that reads "the system does X" is worthless if "X" was generated from the old code. The human review step is where the drift is actually caught.

## When to Apply
- Anyone adding a prediction feature (new event type, new scaling factor, new confidence source): schedule the prompt update work as part of the implementation, not the polish
- Anyone adjusting an existing prediction method (decay rates, weighting coefficients, feature lists): check which prompts reference those values and update them
- Anyone reviewing a PR that touches `woodchopping/predictions/` or `strathmark_adapter.py`: require a prompt-updates-included checkbox before merging
- When Ollama returns predictions that look systematically wrong (too high, too low, biased by an irrelevant factor): check whether a recent feature change left the prompt stale before blaming the model

## Examples

**V4.4 tournament-weighting prompt update** (reconstructed pattern):

```python
# Before (V4.3) — LLM has no idea tournament weighting exists
prompt = f"""
Baseline prediction: {baseline:.1f}s
Wood: {species} at {diameter}mm, quality {quality}/10

Adjust the baseline for wood quality. Return the adjusted time.
"""

# After (V4.4 v2.0) — LLM understands the baseline is already tournament-weighted
prompt = f"""
Baseline prediction: {baseline:.1f}s
Wood: {species} at {diameter}mm, quality {quality}/10
"""

if tournament_weighted:
    prompt += f"""
⚠️ TOURNAMENT CONTEXT
This baseline already incorporates a same-wood result from this tournament
at 97% weight. The competitor chopped this exact wood today in
{tournament_round} at {tournament_time:.1f}s.

Your quality adjustment should be MINIMAL — the wood is PROVEN.
A typical adjustment in this case is ±0.5s, not the usual ±2-5s.
"""

prompt += """
Adjust the baseline for wood quality. Return the adjusted time.
"""
```

The conditional block is the key structural element. When the system *is* using tournament weighting, the prompt surfaces it. When it isn't, the prompt reverts to the simple case. The LLM no longer has to guess.

## Related
- [CLAUDE.md "CRITICAL DEVELOPMENT RULE - LLM PROMPT MAINTENANCE"](../../../CLAUDE.md) — the standing order
- [docs/PROMPT_CHANGELOG.md](../../PROMPT_CHANGELOG.md) — version history of prompt updates
- [docs/PROMPT_ENGINEERING_GUIDELINES.md](../../PROMPT_ENGINEERING_GUIDELINES.md) — broader prompt patterns, principles, pitfalls
- [woodchopping/predictions/ai_predictor.py](../../../woodchopping/predictions/ai_predictor.py) — the time-prediction prompt site
- [woodchopping/simulation/fairness.py](../../../woodchopping/simulation/fairness.py) — the fairness and championship-commentary prompt sites
