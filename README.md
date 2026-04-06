# Woodchopping Handicap System (STRATHEX)

**Version**: 6.0
**Status**: Production Ready
**Last Updated**: March 9, 2026

A data-driven handicap calculation system for woodchopping competitions that combines historical performance analysis, machine learning (XGBoost), and AI-enhanced predictions to create fair, competitive handicaps.

As of V6.0, all handicap calculation, Monte Carlo simulation, and fairness assessment is performed by **STRATHMARK** — a separate, pip-installable Python engine that STRATHEX calls directly. STRATHMARK is installed in editable mode so any improvement to the engine is immediately available to STRATHEX on next run.

---

## Quick Start

### Running the Program

```bash
# Install STRATHEX and all core dependencies (pulls strathmark from GitHub)
pip install -e .              # Core + ML
pip install -e ".[llm]"      # Include Ollama LLM predictor extras
pip install -e ".[dev]"      # Testing and linting tools

# Start the main tournament management program
python MainProgramV5_2.py
```

### Prerequisites

- **Python**: 3.13+
- **Ollama**: Running locally with `qwen2.5:7b` model (for AI predictions, optional)
- **Data File**: `woodchopping.xlsx` in project root
- **STRATHMARK**: Installed automatically as a dependency from
  [github.com/SquirmyWormy275/STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK).
  For local development against an editable checkout, clone the repo as a
  sibling directory and run `pip install -e ../STRATHMARK` after `pip install -e .`.

### Dependency Source of Truth

All runtime and dev dependencies are defined in [pyproject.toml](pyproject.toml).
There is no `requirements.txt`. To add or change a dependency, edit `pyproject.toml`
and reinstall with `pip install -e ".[dev]"`.

---

## Project Structure

```
STRATHEX/
│
├── MainProgramV5_2.py              # Main tournament management interface
├── explanation_system_functions.py  # STRATHEX educational guide for judges
├── config.py                        # STRATHEX configuration settings
├── pyproject.toml                   # Packaging, deps, tooling configuration
├── woodchopping.xlsx                # Historical results database (gitignored)
├── CLAUDE.md                        # Project-level Claude Code guidance
│
├── woodchopping/                    # STRATHEX modular package
│   ├── strathmark_adapter.py        # DataFrame ↔ STRATHMARK typed objects
│   ├── data/
│   │   ├── store_registry.py        # Module-level ResultStore singleton
│   │   └── excel_io.py              # Excel I/O + dual-write to ResultStore
│   ├── handicaps/
│   │   └── calculator.py            # Thin wrapper → strathmark.HandicapCalculator
│   ├── predictions/                 # Prediction methods (Baseline, ML, LLM)
│   ├── simulation/
│   │   ├── monte_carlo.py           # Proxy → strathmark.variance
│   │   └── fairness.py              # Proxy → strathmark.fairness
│   ├── analytics/                   # Performance history, profiling
│   └── ui/                          # User interface modules
│
├── docs/                            # Documentation
│   ├── SYSTEM_STATUS.md             # Current system status report
│   ├── ML_AUDIT_REPORT.md           # ML model audit and validation
│   ├── PROMPT_ENGINEERING_GUIDELINES.md
│   └── ... (other documentation)
│
├── tests/                           # Test scripts
│   └── validation/                  # Backtesting and model comparison suites
│
└── .github/workflows/ci.yml         # Lint, test (Linux+Windows), build verification
```

> **Note:** STRATHMARK is **not** vendored as a subdirectory of this repo.
> It lives in its own GitHub repo at
> [github.com/SquirmyWormy275/STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK)
> and is pulled in as a dependency by `pyproject.toml`. Earlier drafts of
> this README incorrectly described it as a `./STRATHMARK/` subdirectory.

---

## Architecture: STRATHEX + STRATHMARK

### How They Work Together

```
STRATHEX (this program)
  — Tournament management, UI, Excel I/O
  — Calls STRATHMARK for all calculations

STRATHMARK (./STRATHMARK/)
  — Handicap calculation engine
  — Monte Carlo simulation
  — AI fairness assessment
  — SQLite result persistence
  — FastAPI HTTP server (for future web/mobile consumers)
```

STRATHMARK is installed automatically when you `pip install -e .` in STRATHEX —
the dependency is pinned to the `main` branch of the STRATHMARK GitHub repo.

For active development on the engine, clone STRATHMARK as a sibling directory
and reinstall it editable:

```bash
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK
```

Once installed editable, Python reads STRATHMARK source files directly —
**any improvement to STRATHMARK takes effect immediately on next STRATHEX run.**

### SQLite Persistence

STRATHMARK maintains a persistent SQLite database at `~/.strathmark/results.db`.
Every tournament result is automatically saved. Predictions grow more accurate
as more competitions are recorded because the engine learns from all past results.

On startup, STRATHEX migrates all historical Excel results into this database
(idempotent — safe to run multiple times; duplicates are skipped).

### HTTP REST API (Optional — Future Use)

STRATHMARK includes a FastAPI HTTP server for future non-Python consumers:

```bash
pip install strathmark[api]
uvicorn strathmark.api:app --host 0.0.0.0 --port 8000
```

Endpoints: `POST /calculate`, `POST /predict`, `POST /simulate`,
`POST /results`, `GET /results/{name}`, `GET /health`

---

## Core Features

### 1. Multiple Prediction Methods

- **Baseline**: Statistical time-weighted average with QAA diameter scaling
- **ML (XGBoost)**: Separate models for Standing Block (SB) and Underhand (UH)
- **LLM (Ollama)**: AI-enhanced predictions with wood quality reasoning

All methods use **consistent exponential time-decay weighting** (2-year half-life)
to prioritize recent performances over historical peaks.

### 2. Intelligent Prediction Selection (V6.0 — STRATHMARK)

STRATHMARK uses expected-error scoring rather than a fixed cascade:

```
Score = base_error(confidence) + method_penalty + spread_penalty - tournament_bonus

Lower score = preferred prediction

Manual override  → always wins
Panel mark       → last resort
```

Method penalties: +0.5 for LLM, +1.5 if scaled. Tournament bonus: -1.0 when
same-tournament result used (VERY HIGH confidence floor 0.5). Spread penalty
applied when predictions diverge significantly (≥4s or ≥12%).

### 3. Advanced Features

- **Diameter Scaling**: QAA empirical tables (150+ years Australian data)
- **Wood Quality Adjustment**: ±2% per quality point (0-10 scale)
- **Time-Decay Weighting**: Recent performances weighted higher than old results
- **Monte Carlo Simulation**: Validate handicap fairness with 2 million iterations
- **SQLite Persistence**: Results accumulate across competitions automatically (V6.0)
- **Multi-Round Tournaments**: Heats → Semi-finals → Finals
- **Multi-Event Tournaments**: Complete tournament days with multiple independent events
- **Championship Race Simulator**: Predict equal-start race outcomes with AI analysis
- **Prize Money/Payout System**: Configurable payout tracking per placement
- **Bracket Tournaments**: Single and double elimination with AI-powered seeding

### 4. Fairness Metrics

- **Target**: < 1.0s finish time spread (Excellent)
- **Current Performance**: 0.3s - 0.8s spread in testing
- **AAA Rules Compliant**: 3s minimum mark, 180s maximum time

---

## Git Branches

| Branch | Description |
|--------|-------------|
| `main` | **V6.0** — STRATHMARK as authoritative engine, SQLite persistence |
| `v5.2-legacy` | V5.2 — Pure local calculation, no STRATHMARK dependency |

The `v5.2-legacy` branch is maintained for environments where the STRATHMARK
dependency cannot be installed. The prediction methodology is identical.

---

## Event Types

- **SB**: Standing Block
- **UH**: Underhand
- **Future**: 3-Board Jigger (pending more training data)

---

## Testing

```bash
# Install dev tools (pytest, pytest-cov, ruff)
pip install -e ".[dev]"

# Run the full STRATHEX test suite
pytest tests/ -v --cov=woodchopping --cov-report=term-missing

# Skip Ollama-dependent tests (the same flag CI uses)
pytest tests/ -v -m "not ollama"

# Verify STRATHEX → STRATHMARK integration
python -c "from woodchopping.handicaps.calculator import calculate_ai_enhanced_handicaps; print('OK')"
```

Tests marked `@pytest.mark.ollama` require a local Ollama instance running
`qwen2.5:7b` and are skipped in CI.

**Test Results**:
- STRATHMARK: 28/28 passing
- UH: 0.8s spread [EXCELLENT]
- SB: 0.3s spread [EXCELLENT]

---

## Data Requirements

### Excel File Structure

**Sheets Required**:
1. `Competitor`: CompetitorID, Name, Country, State/Province, Gender
2. `wood`: Species, Janka Hardness, Specific Gravity, etc.
3. `Results`: CompetitorID, Event, Time (seconds), Size (mm), Species Code, Quality, HeatID, Date

### Minimum Data for Predictions

- **New Competitor**: 3+ historical results
- **ML Training**: 50+ records per event (UH needs more data)
- **Baseline**: Works with any amount of data (cascading fallback)

---

## Key Concepts

### Time-Decay Weighting

**Formula**: `weight = 0.5^(days_old / 730)`

Recent performances are weighted much higher than old results:

```
Example - Moses (7-year span):
- 2018 peaks (19-22s): weight 0.06 (3%)
- 2023 results (27-28s): weight 0.50 (50%)
- 2025 current (29s): weight 1.00 (100%)
```

### Diameter Scaling

**Tables**: QAA empirical tables (150+ years validated)
**Formula**: `scaled_time = original_time × QAA_factor(from, to, wood_type)`

### Wood Quality Scale

```
10 = Extremely soft → FAST cutting (baseline × 0.90)
5  = Average → NO adjustment (baseline × 1.00)
0  = Extremely hard → SLOW cutting (baseline × 1.10)
```

### Tournament Result Weighting

```
Semi/Final prediction = (today's heat time × 0.97) + (historical avg × 0.03)
```

Same wood across all rounds = most accurate predictor possible.

---

## Production Use

**Recommended for**:
- Missoula Pro-Am
- Mason County Western Qualifier
- Any AAA-sanctioned woodchopping events

**Current Status**: Production Ready

---

## CI/CD

GitHub Actions runs on every push and pull request to `main`:

| Job   | Runs on                          | What it checks |
|-------|----------------------------------|----------------|
| lint  | ubuntu-latest                    | `ruff check .` and `ruff format --check .` |
| test  | ubuntu-latest, windows-latest    | `pytest tests/ -m "not ollama"` with coverage on `woodchopping` |
| build | ubuntu-latest (after lint+test)  | `python -m build` and verify the wheel imports cleanly |

To run the same checks locally:

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest tests/ -v -m "not ollama" --cov=woodchopping
python -m build
```

Tests marked `@pytest.mark.ollama` need a local Ollama instance and are skipped
in CI by the `-m "not ollama"` filter.

---

## Ecosystem

STRATHEX is one of two projects in the woodchopping handicap ecosystem:

- **STRATHEX** (this repo) — full tournament management application: UI,
  Excel I/O, multi-event/multi-round flows, payouts, championship simulator.
- **[STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK)** — the
  pip-installable handicap calculation engine. Other tournament management
  systems can depend on it directly without pulling in STRATHEX's UI layer.

As of V6.0, STRATHEX delegates **all** handicap calculation, prediction
aggregation, Monte Carlo variance modeling, and AI fairness assessment to
STRATHMARK via [woodchopping/strathmark_adapter.py](woodchopping/strathmark_adapter.py).
STRATHEX retains the tournament management surface (rounds, brackets, payouts,
Excel persistence, judge-facing CLI).

---

## Version History

- **V6.0** (Mar 2026): STRATHMARK engine integration, SQLite persistence, HTTP REST API
- **V5.2** (Jan 2026): Tournament payout configuration, position-based draws, connection caching
- **V5.1** (Jan 2026): Comprehensive wood properties, sparse data validation, diameter flagging
- **V5.0** (Jan 2026): Championship Race Simulator, bracket tournaments, prize money system
- **V4.4** (Dec 2025): QAA diameter scaling, tournament result weighting
- **V4.3** (Dec 2025): Time-decay consistency, wood quality integration
- **V4.0** (Dec 2025): Modular architecture, separate SB/UH models

---

**License**: Academic Project
**Author**: Alex Kaper
**AI Assistant**: Claude (Anthropic)
