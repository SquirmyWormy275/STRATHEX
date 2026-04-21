# Architecture

STRATHEX is two systems stapled together:

1. **STRATHEX** (this repo) — the tournament-management surface. CLI, Excel I/O, multi-round/multi-event workflow, payout config, championship simulator, judge-approval UI.
2. **[STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK)** (engine repo) — the pip-installable calculation core. Predictions, Monte Carlo, AAA mark arithmetic, QAA diameter scaling, SQLite persistence, optional HTTP API.

As of V6.0, everything load-bearing (prediction, simulation, fairness assessment) has been extracted into STRATHMARK. STRATHEX talks to it through one adapter file: [`woodchopping/strathmark_adapter.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/strathmark_adapter.py).

## Data flow

```
Excel: woodchopping.xlsx                      SQLite: ~/.strathmark/results.db
     │                                                    │
     └──────────┬──────────────────────┬─────────────────┘
                │                      │
                ▼                      ▼
        STRATHEX adapter ──► STRATHMARK typed objects
        (DataFrame)             (CompetitorRecord, WoodProfile,
                                 HistoricalResult)
                │
                ▼
        STRATHMARK HandicapCalculator.calculate()
        ├─ predictor.py     Baseline + ML (XGBoost) + LLM (Ollama)
        │                   → select_best_prediction() picks winner
        ├─ wood.py          QAA diameter scaling (empirical tables)
        ├─ decay.py         Exponential time-decay (2-year half-life)
        └─ calculator.py    Gap → Mark (floor 3, ceiling 183, rounded)
                │
                ▼
        MarkResult list ──► STRATHEX judge UI (3-column display)
                │
                ▼           ┌────────────────────────────────────────┐
        Optional:           │ Manual overrides are always allowed.  │
        Monte Carlo         │ STRATHEX is decision support, not a   │
        (2M race sim)       │ replacement for the Handicapper —     │
                │           │ AAA Rule 14 is final authority.       │
                ▼           └────────────────────────────────────────┘
        Excel write + ResultStore dual-write
```

## Module map

### STRATHEX — tournament layer

| Path | Responsibility |
|---|---|
| [`MainProgramV5_2.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/MainProgramV5_2.py) | Main menu loop, session state, top-level navigation |
| [`config.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/config.py) | STRATHEX-specific settings (banner strings, CLI options) |
| `woodchopping/strathmark_adapter.py` | DataFrame ↔ STRATHMARK typed objects. The one file where crossing the border happens |
| `woodchopping/data/excel_io.py` | Excel atomic read/write (openpyxl), dual-write to ResultStore |
| `woodchopping/data/store_registry.py` | Module-level ResultStore singleton |
| `woodchopping/handicaps/calculator.py` | Thin wrapper that calls `STRATHMARK.HandicapCalculator` |
| `woodchopping/simulation/monte_carlo.py` | Proxy to `strathmark.variance` |
| `woodchopping/simulation/fairness.py` | Proxy to `strathmark.fairness` |
| `woodchopping/ui/wood_ui.py` | Wood species / diameter / quality prompts |
| `woodchopping/ui/competitor_ui.py` | Roster selection with sparse-data filtering |
| `woodchopping/ui/tournament_ui.py` | Single-event multi-round flow |
| `woodchopping/ui/multi_event_ui.py` | Multi-event tournament day flow |
| `woodchopping/ui/bracket_ui.py` | Single and double elimination |
| `woodchopping/ui/championship_simulator.py` | Equal-start race prediction |
| `woodchopping/ui/payout_ui.py` | Prize money configuration + display |
| `woodchopping/analytics/` | Performance history, competitor profiling |
| `explanation_system_functions.py` | In-app educational wizard (option 8) |

### STRATHMARK — calculation engine

| Module | Responsibility |
|---|---|
| `calculator.py` | Gap logic, mark floor/ceiling, start sheet rendering |
| `predictor.py` | Prediction cascade + expected-error scoring |
| `variance.py` | Absolute ±3s variance model, Monte Carlo (500K–2M iterations) |
| `wood.py` | QAA empirical scaling tables, quality factor |
| `decay.py` | Exponential time-decay (half-life 730 days) |
| `fallback.py` | Panel marks, event baseline fallbacks |
| `store.py` | SQLite ResultStore (`~/.strathmark/results.db`) |
| `db.py` | Supabase/PostgreSQL backend (future) |
| `llm.py` | Ollama HTTP client with connection caching |
| `llm_roles.py` | Fairness narration, anomaly detection, commentary |
| `fairness.py` | AI-assisted fairness assessment |
| `visualization.py` | Plain-text bar charts |
| `analytics.py` | Backtesting, competitor profiling |
| `api.py` | FastAPI HTTP API (`POST /calculate`, `/simulate`, etc.) |

## Key design decisions

### Why a split?

Tournament managers come and go — Missoula-Pro-Am-Manager and future tools all want the same handicap logic without inheriting STRATHEX's CLI, Excel I/O, or roster management. Keeping the engine in a separate pip package means:

- One source of truth for mark math. A bug fix in STRATHMARK is live everywhere instantly.
- Downstream tools pin a version. STRATHEX can ship at its own cadence.
- Non-Python consumers can hit the FastAPI HTTP API instead.

### Why editable install?

`pip install -e ../STRATHMARK` makes STRATHMARK source the live source. Any edit to the engine is picked up on the next STRATHEX run with no rebuild step. This matters because the two repos evolve together — a new feature typically requires changes on both sides, and a slow iteration loop would eat hours per week.

### Why dual-write to both Excel and SQLite?

- **Excel** is the judge's file. It's portable, editable, and familiar. It stays canonical.
- **SQLite** (`~/.strathmark/results.db`) is the engine's learning substrate. Results accumulate across competitions, months, and seasons — not just whatever's in the current workbook. More data → better predictions.

Every save is atomic and writes to both. Startup migration is idempotent (`INSERT OR IGNORE`), so re-running STRATHEX never corrupts history.

### Why an adapter layer?

STRATHEX is DataFrame-native (historical reasons — pandas was the tool at hand when it started). STRATHMARK is strictly typed (`@dataclass` everywhere, no pandas). The adapter is 200 lines of glue that converts one to the other. Keeping it isolated means engine changes don't force STRATHEX refactors and vice versa.

## Related repos

- [**STRATHMARK**](https://github.com/SquirmyWormy275/STRATHMARK) — the engine. Pip-installable. Ships its own CI, wiki, tests.
- [**Missoula-Pro-Am-Manager**](https://github.com/SquirmyWormy275) *(sibling, future)* — a lighter-weight tournament manager for the Missoula event. Will depend on STRATHMARK directly.
- See [Ecosystem](Ecosystem) for the full picture.
