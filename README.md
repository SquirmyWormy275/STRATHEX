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
# Install STRATHMARK engine (editable — live integration)
pip install -e ./STRATHMARK

# Start the main tournament management program
python MainProgramV5_2.py
```

### Prerequisites

- **Python**: 3.13+
- **Ollama**: Running locally with `qwen2.5:7b` model (for AI predictions)
- **Data File**: `woodchopping.xlsx` in project root
- **STRATHMARK**: Installed from the `STRATHMARK/` subdirectory (see above)

### Required Python Packages

```bash
pip install pandas openpyxl xgboost scikit-learn requests numpy
```

---

## Project Structure

```
woodchopping-handicap-system/
│
├── MainProgramV5_2.py              # Main tournament management interface
├── explanation_system_functions.py  # STRATHEX educational guide for judges
├── config.py                        # STRATHEX configuration settings
├── woodchopping.xlsx                # Historical results database
├── tournament_state.json            # Saved tournament state
│
├── STRATHMARK/                      # Pip-installable handicap engine (V6.0)
│   └── strathmark/
│       ├── calculator.py            # HandicapCalculator — mark assignment
│       ├── predictor.py             # Baseline, ML, LLM predictions
│       ├── variance.py              # Monte Carlo simulation
│       ├── fairness.py              # AI fairness assessment
│       ├── store.py                 # SQLite persistence (ResultStore)
│       ├── llm.py                   # Ollama integration
│       ├── visualization.py         # Simulation charts
│       ├── analytics.py             # Backtesting and profiling
│       ├── wood.py                  # QAA scaling tables
│       ├── decay.py                 # Time-decay weighting
│       ├── fallback.py              # Cascading prediction fallback
│       ├── config.py                # Engine configuration
│       └── api.py                   # FastAPI HTTP REST API
│
├── woodchopping/                    # STRATHEX modular package
│   ├── data/
│   │   ├── store_registry.py        # Module-level ResultStore singleton
│   │   └── excel_io.py              # Excel I/O + dual-write to ResultStore
│   ├── handicaps/
│   │   └── calculator.py            # Thin wrapper → HandicapCalculator
│   ├── strathmark_adapter.py        # DataFrame ↔ STRATHMARK typed objects
│   ├── predictions/                 # Prediction methods (Baseline, ML, LLM)
│   ├── simulation/
│   │   ├── monte_carlo.py           # Proxy → strathmark.variance
│   │   └── fairness.py              # Proxy → strathmark.fairness
│   └── ui/                          # User interface modules
│
├── docs/                            # Documentation
│   ├── SYSTEM_STATUS.md             # Current system status report
│   ├── ML_AUDIT_REPORT.md           # ML model audit and validation
│   └── ... (other documentation)
│
└── tests/                           # Test scripts
```

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

STRATHMARK is installed with `pip install -e ./STRATHMARK` (editable mode).
Python reads STRATHMARK source files directly — no rebuild required after changes.
**Any improvement to STRATHMARK takes effect immediately on next STRATHEX run.**

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
# Run STRATHMARK engine tests (28 tests)
python -m pytest STRATHMARK/tests/ -v

# Verify STRATHEX → STRATHMARK integration
python -c "from woodchopping.handicaps.calculator import calculate_ai_enhanced_handicaps; print('OK')"

# Run legacy STRATHEX tests
python tests/test_both_events.py
python tests/test_uh_predictions.py
```

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
