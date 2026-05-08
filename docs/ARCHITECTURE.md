# Architecture

This document describes how STRATHEX is structured today, what data it persists, where the trust boundaries are, how the prediction stack works, what is hardened for production, and what I would do differently if starting again. It is written for engineering hiring managers and integrators who need to evaluate the system at the design level. The corresponding code is the source of truth; this document cites file paths and line ranges throughout.

## System overview

STRATHEX is a Python 3.13 CLI application that manages multi-round and multi-event woodchopping tournaments. It owns three concerns: judge-facing user interaction, persistent tournament data, and tournament workflow orchestration. It does not own any handicap calculation logic. As of V6.0 all calculation, Monte Carlo simulation, and AI fairness assessment is delegated to **STRATHMARK**, a separate pip-installable engine. STRATHEX speaks to STRATHMARK exclusively through one file, [woodchopping/strathmark_adapter.py](../woodchopping/strathmark_adapter.py), which converts pandas DataFrames to STRATHMARK's typed dataclasses and back.

```text
+--------------------------------------------------+      +--------------------------------------+
|  STRATHEX (CLI tournament manager)               |      |  STRATHMARK (handicap engine)        |
|                                                  |      |                                      |
|  MainProgramV5_2.py    main loop, menus          |      |  calculator.py    HandicapCalculator |
|  config.py             AAA constants (frozen)    |      |  predictor.py     prediction cascade |
|                                                  | pip  |  variance.py      Monte Carlo        |
|  woodchopping/                                   | dep  |  fairness.py      AI assessment      |
|    ui/        judge CLI, menu trees, banners     | -->  |  decay.py         time-decay         |
|    data/      Excel I/O, store registry          |      |  wood.py          QAA scaling        |
|    handicaps/ thin wrappers (proxy to engine)    |      |  store.py         SQLite ResultStore |
|    simulation/proxy modules                      |      |  api.py           FastAPI HTTP layer |
|    analytics/ history, profiling                 |      |  llm.py           Ollama client      |
|    strathmark_adapter.py *                       |      |  migrations/      SQL                |
+--------------------------------------------------+      +--------------------------------------+
* the only file in STRATHEX that imports strathmark
```

The `woodchopping/handicaps/calculator.py` and `woodchopping/simulation/*` modules are deliberately thin: they validate inputs, call STRATHMARK, and translate the result. This keeps the boundary stable and lets STRATHMARK be reused in other tournament software, including [downstream event-day managers](../wiki/Ecosystem.md), without dragging in STRATHEX's CLI or Excel dependencies. Independence is verifiable: STRATHMARK has zero imports from `woodchopping.*`.

## Data model

Two persistent stores exist by design.

**Excel** (judge-canonical) lives at the project root as `woodchopping_clean.xlsx`, with three sheets:

- `Competitor`: `CompetitorID, Name, Country, State/Province, Gender`. The roster.
- `wood`: species and physical properties (Janka hardness, specific gravity) used by the LLM and ML predictors.
- `Results`: `CompetitorID, Event, Time, Species, Diameter, Quality, HeatID, Date`. The historical performance record.

The Excel file is canonical because judges already know how to edit and back it up. STRATHEX never overwrites a sheet. Appends are atomic via `openpyxl` with explicit cell writes (see `woodchopping/data/excel_io.py`). Deliberately not using `pandas.to_excel`, which rewrites the entire workbook and is unsafe under partial failures.

**SQLite ResultStore** (engine-canonical) lives at `~/.strathmark/results.db`, owned by STRATHMARK. Schema is one table, `results`, with a `UNIQUE(competitor_name, heat_id, event_code, time_seconds)` constraint and an index on `(competitor_name, event_code)` (see `strathmark/store.py`). Three migrations are tracked under `strathmark/migrations/`: source tracking, ML state tables, and row-level-security reframe.

On every STRATHEX startup the Excel `Results` sheet is bulk-imported into the ResultStore via `INSERT OR IGNORE`, making the migration idempotent. Every tournament round is dual-written: appended to Excel (judge keeps their workbook) and inserted into SQLite (engine accumulates learning across competitions). The two stores are not symmetric: SQLite has more history because the user can carry it across machines and reuse it for prediction in events that don't ship the Excel file.

A `CompetitorRecord` (STRATHMARK type) wraps `name`, a list of `HistoricalResult`s, optional `division` for panel-mark fallback, and optional `tournament_time` for same-wood 97% weighting in semis and finals. The `WoodProfile` is just `species, diameter_mm, quality`.

## Trust boundary and data integrity

STRATHEX is a single-user CLI on a judge's laptop, so there is no user-auth model. The actual integrity boundary is between *judge input* and *predictor output*. Three controls exist:

1. **Sparse-data filtering** in [woodchopping/data/excel_io.py](../woodchopping/data/excel_io.py) and `strathmark/predictor.py` rejects competitors with fewer than `MIN_HISTORICAL_TIMES = 3` historical results before they reach the prediction cascade. This was added after a real incident where a one-result competitor crashed the LLM with a malformed history string. See [docs/solutions/data-integrity/sparse-competitor-data-fallback.md](solutions/data-integrity/sparse-competitor-data-fallback.md).
2. **Wood quality scale validation** rejects values outside `[0, 10]`. The convention is documented in [docs/solutions/data-integrity/wood-quality-scale-inversion.md](solutions/data-integrity/wood-quality-scale-inversion.md). Historical data was all recorded as 5 (the average) and a sign-inversion bug in the quality multiplier silently passed lint until a human noticed harder wood was producing faster predicted times.
3. **Idempotent migration** lets a judge re-run STRATHEX after a crash without duplicating rows in either store.

The trust model assumes judges are not hostile but *can be hurried*. Errors must be specific (`Competitor 47 not in roster. Valid range: 1-32`) and the system must never silently fall back to a wrong answer. The predictor returns `None` (not zero, not a baseline) when it cannot produce a confident time, and `HandicapCalculator` then falls back to panel-mark logic with VERY LOW confidence.

## Prediction stack deep dive

Three predictors run for every competitor:

- **Baseline:** time-decayed weighted average over historical results in the same event, with QAA-table diameter scaling and a wood-quality multiplier. Time-decay weight is `0.5 ** (days_old / 730)` (2-year half-life). Ground in `strathmark/predictor.py::predict_baseline`.
- **ML (XGBoost):** separate models for Standing Block and Underhand. Features include diameter, quality, species hardness/density, time-decayed history aggregates, and recent-form deltas. SB model: MAE 2.55s, R² 0.989. UH model: MAE 2.35s, R² 0.878 (UH has fewer training rows; explicit in [docs/ML_AUDIT_REPORT.md](ML_AUDIT_REPORT.md)).
- **LLM (optional):** Ollama with `qwen2.5:7b` reads a structured prompt covering the competitor's recent results, the wood properties, and the tournament context. The prompt explicitly tells the LLM about same-wood tournament weighting (otherwise it double-counts). Discipline for this prompt lives in [docs/PROMPT_ENGINEERING_GUIDELINES.md](PROMPT_ENGINEERING_GUIDELINES.md) with version history in [docs/PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md).

V6.0 replaced the previous fixed-priority cascade (LLM > ML > Baseline) with **expected-error scoring**:

```text
score = base_error(confidence) + method_penalty + spread_penalty - tournament_bonus
```

`method_penalty` adds 0.5 for LLM, 1.5 for any prediction that required diameter scaling. `tournament_bonus` subtracts 1.0 when a same-tournament heat result is being used (97/3 weighted with historical baseline). `spread_penalty` activates when predictions disagree by ≥4s or ≥12%. Lower score wins. Manual override always wins; panel mark is last resort. This is in `strathmark/predictor.py::select_best_prediction`.

The 97/3 weighting reflects the empirical fact that wood from this morning's heats is the same physical wood the same competitor will cut in this afternoon's final. A heat result on this wood is far more predictive than a year-old result on different wood, regardless of how good the historical model is.

## Production hardening

- **CI matrix** ([.github/workflows/ci.yml](../.github/workflows/ci.yml)) runs ruff lint, ruff format check, pytest with coverage on Ubuntu and Windows, and a wheel build with import verification on every push and pull request.
- **Test suite:** 15 STRATHEX test files under `tests/` plus 7 validation suites under `tests/validation/` (backtesting, model comparison, fairness convergence). STRATHMARK ships its own 44-file test suite. The `ollama` pytest marker makes Ollama-dependent tests skippable in CI.
- **Frozen-dataclass config:** AAA rule constants (`MIN_MARK_SECONDS=3`, `MAX_TIME_LIMIT_SECONDS=180`, `PERFORMANCE_VARIANCE_SECONDS=3`) are encoded in `config.py` as `@dataclass(frozen=True)` so they cannot be silently mutated at runtime.
- **Documented solutions repo:** [docs/solutions/](solutions/) catalogues 13 past problems and their fixes with YAML frontmatter (`module`, `tags`, `problem_type`, `severity`) so future contributors can grep by domain instead of re-debugging from scratch.
- **Versioned wiki:** 17 judge-facing pages live in `wiki/` and are published via `wiki/publish.sh` so the public GitHub wiki is reproducible from a commit.

## Failure modes and what I would do differently

1. **Excel as canonical store is fragile.** Judges email the workbook around, edit cells in Excel, and sometimes corrupt the schema. The `solutions/data-integrity/excel-results-schema-column-mismatch.md` doc captures one such incident. If I were starting again I would make SQLite canonical from day one and treat Excel as a read-only export. The judge-portability argument turned out to be weaker than feared; tournament organizers actually prefer a CSV export.
2. **Two predictors that disagree is harder than one predictor that's wrong.** The expected-error scoring is good, but when ML says 27s and LLM says 33s the scoring picks one and the judge has no way to see *why* the disagreement matters. A future version should surface the spread to the judge with confidence-weighted bands instead of a single number.
3. **The 97/3 weighting is a magic constant.** It came from one weekend of empirical tuning. It is probably right within ±3 percentage points but I never re-derived it after the V5.0 rewrite, and same-wood predictive power probably varies by event type. Calibrating per (event, diameter) bucket is a reasonable next step.
4. **The CLI's banner-alignment standing rule is enforced by convention, not test.** Misalignment shipped twice in V5.x because reviewers eyeballed the diff. A simple test that imports each banner-printing function, captures stdout, and asserts every line is exactly 70 characters wide would have caught both.
5. **STRATHMARK's editable install is an unergonomic dev loop.** `pip install -e ../STRATHMARK` plus a STRATHEX run to test an engine change works but it is noticeably slower than the previous "just edit a file in the same repo" workflow. A faster local feedback loop, perhaps via a `make dev` target that watches both repos, would pay for itself.
6. **No multi-judge scenario exists.** The trust model assumes one judge with one laptop. Running two simultaneous events with two judges entering results into two STRATHEX instances would race on the SQLite ResultStore. The fix is straightforward (add an event-scoped lock or serialize via the FastAPI HTTP layer) but it is not implemented.
