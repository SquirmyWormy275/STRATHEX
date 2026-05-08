# Case study: STRATHEX

## Context

I built STRATHEX as a personal project to solve a specific problem in competitive woodchopping: handicap calculation that is mathematically defensible to a tournament organizer and accurate enough that mixed pro/amateur fields produce real races. Australian woodchopping has 150+ years of empirical handicapping practice, codified in the AAA Competition Rules and the QAA Handicap Book. The US scene runs much smaller events, has no equivalent institutional knowledge, and the tools that exist are mostly spreadsheets that do linear interpolation by hand. The opportunity was to combine the Australian empirical tables with modern prediction methods (XGBoost, an LLM trained on enough text to reason about wood-quality variation) and produce a tool a US show runner could actually use.

The system is now in V6.0. The CLI runs full multi-round and multi-event tournaments, validates fairness with 2 million Monte Carlo races per event, and holds finish-time spread between **0.3 and 0.8 seconds** in production testing against a target of <1.0s. The handicap engine was extracted into a separate pip-installable package, **STRATHMARK**, in March 2026 so other tournament software can depend on the math without inheriting STRATHEX's CLI. STRATHMARK has its own 44-file test suite and 707 passing tests. STRATHEX itself is roughly 5,400 lines of top-level Python plus a 52-module `woodchopping/` package.

## Constraints

**Solo developer, no production traffic, no paying customers yet.** Everything I built had to be defensible to me first; there was no team review and no QA function. I leaned heavily on tests, ruff, and a documented-solutions knowledge store ([docs/solutions/](solutions/)) to keep myself honest across long gaps between sessions.

**Windows-native, single-laptop deployment.** Tournament judges run this on a $400 laptop in a tent on tournament day. No server. No internet (Ollama has to run locally). No "just SSH in" recovery path. Every error message had to be actionable on a 13-inch screen with sawdust on the keyboard.

**Plain ASCII only.** Box-drawing characters (`╔╗╚╝║═`) but no emojis, no ANSI color codes, no Unicode that might mojibake under Windows code page CP-1252. This was learned the hard way; see [docs/solutions/runtime-errors/unicode-ascii-windows-terminal.md](solutions/runtime-errors/unicode-ascii-windows-terminal.md).

**Excel as the judge's canonical file.** Judges already know how to edit Excel and email workbooks to each other. The system had to round-trip Excel cleanly without rewriting sheets, even when the engine acquired SQLite later.

**Real wood, real measurements, no synthetic shortcuts.** The QAA empirical scaling tables are the ground truth for diameter scaling. I could not invent a smooth functional form that contradicted them, even when the tables had visibly noisy entries.

## Key technical decisions

### 1. Absolute variance, not proportional variance

**Situation.** The Monte Carlo fairness validator simulates each race with a per-competitor random performance variation. The natural choice is proportional: a 30s chopper varies by ±5%, a 60s chopper varies by ±5%. I used proportional variance for two weeks.

**Decision.** Switched to absolute ±3s for every competitor, regardless of skill level.

**Rationale.** Proportional variance gave faster competitors a smaller absolute range and therefore a higher win rate in the simulation. The win-rate spread under proportional variance was 31% across a balanced field; under absolute variance it was 6.7%. The asymmetry was not a fairness model artifact. It was a *physical* fact, because the noise sources that dominate (technique slip, wood-grain irregularity, axe-edge variation) affect cuts in absolute terms, not proportional terms. A 0.5-second hesitation is a 0.5-second hesitation regardless of how fast the chopper is overall.

**Lesson.** When choosing between two plausible models, the one whose error sources you can name in a sentence is usually right. I had a story for absolute variance ("the axe slips for the same fraction of a second") and no story for proportional variance ("uh, faster choppers also have larger absolute errors?").

### 2. Extracting STRATHMARK from STRATHEX in V6.0

**Situation.** Through V5.x the calculation engine, the Monte Carlo, the LLM client, and the SQLite layer all lived inside STRATHEX as files in `woodchopping/`. A separate request came in to use the math in a different tournament management surface. Embedding it as a Git submodule of STRATHEX worked but forced the consumer to clone all of STRATHEX's CLI dependencies.

**Decision.** Moved every calculation module into a new repo, **STRATHMARK**, published it as a pip-installable package, and replaced STRATHEX's calculation modules with thin wrappers that delegate via [woodchopping/strathmark_adapter.py](../woodchopping/strathmark_adapter.py). The adapter is the only file in STRATHEX that imports `strathmark`.

**Rationale.** Two distinct buyers exist. Tournament organizers want a Windows-native CLI app and don't care about the engine. Software developers want the engine and don't want a CLI. A monorepo serves neither well; two repos with a stable adapter serve both. The architecture-decision doc is at [docs/solutions/architecture-decisions/strathmark-extraction-v6.md](solutions/architecture-decisions/strathmark-extraction-v6.md).

**Lesson.** Two-buyer extractions are worth it. Premature abstraction of a single concern is not. The signal that justified this split was concrete: a real second consumer existed and needed only the engine.

### 3. Expected-error scoring instead of fixed prediction cascade

**Situation.** Through V5.x the predictor cascade was hardcoded: LLM if available, else ML if trained, else baseline. This worked badly when the LLM had VERY LOW confidence (sparse history) and the baseline was actually more reliable. The system would dutifully use a 35% LLM prediction and ignore a 75% baseline.

**Decision.** Replaced the fixed cascade with `score = base_error(confidence) + method_penalty + spread_penalty - tournament_bonus`. Lower score wins.

**Rationale.** The right predictor depends on the data, not on the priority list. A high-confidence baseline beats a low-confidence LLM. A scaled prediction (different diameter than what the competitor has historical data for) deserves a penalty, because diameter scaling compounds error. Same-tournament heat results deserve a bonus, because they are physically the same wood.

**Lesson.** Decision rules driven by confidence almost always beat decision rules driven by method type. The right question is "how much do I trust *this specific prediction*" rather than "which method's predictions do I prefer in general."

### 4. 97% weighting for same-wood tournament results

**Situation.** Generating semi-final and final marks from heat results: should the system trust today's heat time (which is on the same wood) or the historical baseline (which has years of data)?

**Decision.** Weight `prediction = (today_heat_time × 0.97) + (historical_baseline × 0.03)` whenever a same-tournament heat result exists.

**Rationale.** Wood is variable. Quality 5 oak today is not Quality 5 oak from a competition six months ago. The same physical block under the axe right now is the most predictive signal available. The historical baseline still contributes 3% as a sanity check (the heat could have been a fluke), but it cannot dominate.

**Lesson.** The empirical constant (97 vs. 95 vs. 99) is less important than the principle (same-wood data dominates historical data). I never re-derived 97% rigorously; it came from one weekend of tuning. I would not change the structure of this decision but I would calibrate per (event, diameter) bucket if I rebuilt it. See [docs/ARCHITECTURE.md](ARCHITECTURE.md) failure mode #3.

### 5. Dual-write Excel and SQLite

**Situation.** Excel is what judges expect. SQLite is what an engine that wants to learn across competitions needs. I had to pick one or do both.

**Decision.** Both. Every result write goes to both stores. Startup migration imports Excel into SQLite via `INSERT OR IGNORE`, so the operation is idempotent.

**Rationale.** Excel keeps the judge's workflow uninterrupted. SQLite gives STRATHMARK a learning substrate that grows across competitions, machines, and seasons. The cost is one extra write per result, which is negligible. The risk (the two stores diverging) is mitigated by making Excel canonical and SQLite a derived view that can be rebuilt by re-importing.

**Lesson.** Dual-write is a valid pattern when one store is canonical and the derived store is reproducible from it. It would not be a valid pattern if both stores were authoritative for different fields, because then divergence would be unrecoverable.

## What I would do differently

If I were starting STRATHEX again, the biggest change would be **flipping the canonicality of Excel and SQLite**. SQLite as the source of truth, Excel as a read-only export. The argument for Excel canonicality was judge familiarity, but in practice judges are happy with a CSV export of the database, and SQLite eliminates a class of schema-drift bugs that have eaten roughly two days of debugging across the project's lifetime. The migration would be straightforward (the dual-write already exists, just remove the Excel-canonical assumption).

Second, **I would build the prediction-disagreement UI before shipping**. The current system shows three predictions and picks one. When they disagree by 5+ seconds, the judge sees only the winning number and has to dig into the explanation text to understand the disagreement. A confidence-band visualization would make the disagreement structural and turn judge intuition into a meaningful tiebreaker. This is not technically hard; it is just not built.

Third, **the 97/3 tournament weighting deserves per-bucket calibration**. The current single global constant came from manual tuning on one event. Same-wood predictive power likely varies systematically by event type (UH may be less wood-sensitive than SB), diameter, and species. A backtest harness over the SQLite ResultStore could derive bucket-specific weights in a weekend.

Fourth, **CLI banner alignment should be enforced by tests**. The standing rule on banner geometry (70-char total, `.center(68)` for content) was violated twice during V5.x and not caught in review. A simple test that imports each banner-printing function, captures stdout, and asserts line length would have caught both. I added the standing rule, then re-violated it; the rule did not save me.

Fifth, **one-judge concurrency is a real limit**. The system assumes one judge per laptop. Running two simultaneous events on two laptops races on the SQLite ResultStore. The fix is to serialize through the FastAPI HTTP layer (which already exists in STRATHMARK), not to add file locks. I have not done this because no real two-judge scenario has surfaced, but it is the next architectural step.

## Outcomes

- **Production fairness:** finish-time spread between 0.3 and 0.8 seconds, against a target of <1.0s. Win-rate spread under 2%.
- **Predictor accuracy:** SB MAE 2.55s, R² 0.989. UH MAE 2.35s, R² 0.878.
- **Test coverage:** 15 STRATHEX test files plus 7 validation suites; STRATHMARK has 44 test files and ~707 tests passing. Both repos run lint + test + build verification on Ubuntu and Windows for every push.
- **Engine extraction:** STRATHMARK shipped as a separate pip-installable package in V6.0. Verified independent (zero imports from STRATHEX). FastAPI HTTP layer with six endpoints exposes the engine to non-Python consumers.
- **Knowledge store:** 13 documented solutions in [docs/solutions/](solutions/) plus a 17-page judge-facing wiki in `wiki/`.
- **Concrete deliverables:** multi-round tournaments, multi-event tournament days, single/double-elimination brackets, equal-start championship simulator with 2M Monte Carlo iterations and AI commentary, prize-money payout tracking, full Excel I/O round-trip, SQLite persistence with idempotent migration, AAA + QAA rule compliance encoded as frozen-dataclass invariants.
