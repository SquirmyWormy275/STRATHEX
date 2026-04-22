---
title: Judge UI must minimize workflow change under time pressure — features that add steps lose to features that don't
date: 2026-04-21
category: best-practices
module: ui
problem_type: best_practice
component: tooling
severity: medium
applies_when:
  - Adding any new UI feature to tournament flow (heats, results entry, competitor selection)
  - Redesigning existing UI for clarity or speed
  - Reviewing whether a UX improvement is actually an improvement
  - Evaluating feature requests against judge workflow
related_components:
  - development_workflow
tags: [ui, judge-workflow, time-pressure, feature-simplicity, rollback, v5-1]
---

# Judge UI must minimize workflow change under time pressure — features that add steps lose to features that don't

## Context
STRATHEX is CLI software run by tournament judges during live woodchopping competitions. Judges operate under sustained time pressure — between heats, with competitors waiting, often with the next round scheduled within minutes. Any UI feature that adds an interaction step, breaks muscle memory, or requires the judge to *think about the UI* costs real time and increases error rate. Polish that works in a development environment can make things worse in the field.

The V5.1 overhaul (January 2026) was explicit about this: the menu structure was reorganized by workflow phase (Setup → Pre-Competition → Day-Of → Completion), keyboard shortcuts were added for common operations (`s` to save, `q` to quit, `h` for help), and each error message became actionable. Features that improved judge speed were kept. Features that looked helpful but slowed judges down were rolled back.

## Guidance
**Three operational rules, learned from actual rollbacks:**

### 1. Minimize workflow change
The existing workflow — sequential numeric selection from a printed roster list — is fast because judges memorize it. Adding a search filter, a fuzzy matcher, or a "recently used" section changes the interaction model. Even when the new model is objectively faster in the abstract, judges in a live tournament are not in the abstract — they are in muscle-memory mode, and a change forces them to re-engage conscious attention.

Before adding a UI feature, ask: *does this require the judge to interact differently than they do today?* If yes, the feature has to pay for that cost with a significant speed or error-rate improvement, tested against the actual workflow. "Might be nicer" is not enough.

### 2. Live counters over dialogs
Feedback that appears *in the flow* — "3 of 8 competitors selected" updating as the judge types numbers — beats feedback that requires a confirmation dialog. Dialogs interrupt; counters accompany. The V5.1 overhaul kept every live counter that was prototyped and rolled back every confirmation dialog that was prototyped, because the counters never slowed judges down and the dialogs always did.

### 3. Actionable errors over generic errors
"Error: invalid input" is useless. "Competitor 47 not in roster. Valid range: 1-32. Press Enter to retry." lets a judge fix the problem without reading a manual. The [error_display.py](../../../woodchopping/ui/error_display.py) module enforces the actionable-error pattern — every error includes (a) what went wrong, (b) what the valid options are, and (c) what to press next.

## Why This Matters
**Tournament-day cost compounds.** A feature that saves 2 seconds per interaction *and* adds 5 seconds to the first-time interaction loses on opening-day tournaments. A feature that saves 2 seconds per interaction *and* doesn't change first-time interactions wins from day one. Every UI decision must be evaluated against this asymmetry.

**The system is being considered for Missoula Pro-Am (April 24-25, 2026) and Mason County Western Qualifier.** These are real competitions with entry fees, prize money, and judges who will be evaluated by the event organizers. A UI that slows the tournament down reflects badly on the system regardless of how clever its features are.

**Strategic context: STRATHEX has two roles simultaneously.** It is a demo platform that sells the STRATHMARK engine to developer integrators *and* a standalone tool for event organizers who don't have their own software. The retro CLI aesthetic is intentional, not a limitation — it signals "field-ready, low-friction, minimal infrastructure required" to the target buyer. Changes should be evaluated against both roles: does this improve demo impact *and* tournament usability?

## When to Apply
- Any PR touching files in [woodchopping/ui/](../../../woodchopping/ui/)
- Feature requests from non-judges ("it would be nice if...") — always test against judge workflow before implementing
- Any proposal to replace the sequential numeric selection pattern — the bar is high
- Any proposal to add keyboard shortcuts, dialogs, or multi-step flows — prototype, test with a judge if possible, be ready to roll back

## Examples

**Rolled back — type-to-search filter in single-event competitor selection** (January 2026):

A search filter was added to the competitor selection UI, allowing judges to type a prefix to filter the roster. It passed development review. The user tested it and immediately rolled it back:

> "Hey I just tested this feature and it makes things worse. Just go back to the way things were done before."

*Why it failed:* the existing workflow (read number from printed roster, type number, see confirmation) is fast and familiar. The search filter added an extra interaction (choosing between "search" and "number entry") that slowed judges down rather than helping. Judges who already know the competitor numbers gain nothing; judges who don't know the numbers are already reading from a printed list. The filter optimized for a case that didn't exist.

**Kept — live "X of Y selected" counter:**

During the same V5.1 cycle, a live counter was added to the competitor selection UI showing "3 of 8 selected" as the judge typed. It was kept because:
- It accompanies the existing workflow rather than replacing it
- It provides feedback the judge can use to catch over/under-selection without adding a confirmation step
- It works identically on first use and tenth use — no learning curve

**Abandoned before implementation — "Recently used competitors" feature:**

The idea was to show recently-used competitors at the top of the selection list for faster access. On review, it was realized that in tournament mode, judges assign competitors one at a time by workflow position, not by searching from a list. The "recently used" concept didn't match the actual usage pattern. Abandoned at the design stage. *Lesson: different modes of the same UI can have different ergonomics; design for the actual usage pattern, not the imagined one.*

**Abandoned before implementation — sports-betting optimization for the Championship Simulator:**

A user asked whether the Championship Simulator could be tuned for betting-profit optimization (traditional format and Calcutta). The AI assistant refused the gambling framing. The request was reframed as *accuracy improvement* and *"what-if" matchup analysis* — which served the same underlying need (understanding who's likely to win) without the betting framing. Era normalization (adjusting historical times to a reference year) and wood-swap sensitivity analysis (showing how the podium shifts as species/quality/size change) were added as the legitimate replacements.

## Related
- [CLAUDE.md "Typical Judge Workflow"](../../../CLAUDE.md) — canonical 9-step workflow
- [wiki/Tournament-Workflow.md](../../../wiki/Tournament-Workflow.md) — judge-facing workflow explanation
- [woodchopping/ui/error_display.py](../../../woodchopping/ui/error_display.py) — actionable-error implementation
- [woodchopping/ui/tournament_status.py](../../../woodchopping/ui/tournament_status.py) — live progress tracker
- [woodchopping/ui/championship_simulator.py](../../../woodchopping/ui/championship_simulator.py) — era normalization, wood-swap sensitivity as the non-gambling analytical features
- [docs/solutions/architecture-decisions/strathmark-extraction-v6.md](../architecture-decisions/strathmark-extraction-v6.md) — the strategic framing (CLI is intentional, dual role)
