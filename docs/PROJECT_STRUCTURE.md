# Project Structure - Quick Reference

**Last Updated**: April 21, 2026

---

## Root Directory (Clean!)

```
woodchopping-handicap-system/
│
├── README.md                      # ← START HERE: Project overview
├── CLAUDE.md                      # AI assistant & architecture guide
├── MainProgramV5_2.py             # ← RUN THIS: Main program
├── config.py                      # System configuration
├── woodchopping.xlsx              # Historical results database
├── tournament_state.json          # Saved tournament state
│
├── FunctionsLibrary.py            # Legacy functions (being phased out)
├── explanation_system_functions.py # Legacy explanations
│
├── woodchopping/                  # Main package (modular code)
│   ├── data/                      #   Data loading & validation
│   ├── handicaps/                 #   Handicap calculation
│   ├── predictions/               #   Baseline, ML, LLM predictions
│   ├── simulation/                #   Monte Carlo fairness
│   └── ui/                        #   User interface
│
├── STRATHMARK/                    # Pip-installable handicap engine (own git repo)
│   ├── strathmark/                #   Pure calculation core (no UI, no Excel)
│   ├── tests/                     #   28 unit tests (all passing)
│   ├── pyproject.toml
│   └── README.md
│
├── docs/                          # All documentation (organized!)
│   └── solutions/                 #   Documented solutions to past problems (ce:compound)
├── wiki/                          # Versioned GitHub Wiki source + publish.sh sync script
└── tests/                         # Test scripts + conftest.py (collection rules, ollama/strathmark markers)
```

---

## What's Where

### Want to USE the program?
```
1. Open: MainProgramV5_2.py
2. Read: docs/ReadMe.md (user manual)
```

### Want to UNDERSTAND the system?
```
1. Read: README.md (project overview)
2. Read: docs/SYSTEM_STATUS.md (detailed status)
3. Read: docs/INDEX.md (documentation guide)
```

### Want to SEE how it works?
```
1. Run: tests/test_both_events.py
2. Review: docs/ML_AUDIT_REPORT.md
```

### Want to MODIFY the code?
```
1. Read: CLAUDE.md (architecture)
2. Explore: woodchopping/ package
```

---

## Documentation Organization

All documentation now in `docs/`:

### Essential Reading
- **INDEX.md** - Documentation index (start here!)
- **SYSTEM_STATUS.md** - Current system capabilities
- **ReadMe.md** - User manual & function reference

### Technical Documentation
- **ML_AUDIT_REPORT.md** - ML model audit & validation
- **HANDICAP_SYSTEM_EXPLAINED.md** - How handicaps work
- **NewFeatures.md** - Planned enhancements
- **CHECK_MY_WORK_FEATURE.md** - Check My Work validation system
- **QAA_INTERPOLATION_IMPLEMENTATION.md** - Quality/Age/Axe interpolation

---

## Testing Organization

All tests now in `tests/`:

### Main Tests
- **conftest.py** - Collection rules: skips script-style files pytest can't inject, and skips data-dependent tests in `test_baseline_hybrid.py` when `woodchopping.xlsx` is absent (CI does not ship the production database)
- **test_baseline_hybrid.py** - Unit tests for the baseline/hybrid predictor
- **test_both_events.py** - Comprehensive SB & UH validation (script-style, not collected by pytest)
- **test_uh_predictions.py** - UH-specific prediction tests (script-style, not collected by pytest)
- **validation/test_model_comparison.py** - LLM model comparison (marked `pytest.mark.ollama`, skipped in CI)

### Registered markers (see `pyproject.toml`)
- `ollama` — tests that require a local Ollama instance (CI runs with `-m "not ollama"`)
- `strathmark` — tests that exercise the strathmark engine directly

**Run tests (CI-equivalent)**:
```bash
pytest tests/ -v -m "not ollama"
```

**Run a single benchmark script**:
```bash
python tests/test_both_events.py
```

---

## Code Organization (woodchopping/ package)

```
woodchopping/
│
├── data/
│   ├── __init__.py                # Data exports
│   └── excel_io.py                # Excel loading & validation
│
├── handicaps/
│   ├── __init__.py
│   └── calculator.py              # Handicap calculation logic
│
├── predictions/
│   ├── __init__.py
│   ├── baseline.py                # Statistical predictions + time-decay
│   ├── ml_model.py                # XGBoost training & prediction
│   ├── llm.py                     # Ollama API integration
│   ├── ai_predictor.py            # LLM prediction logic
│   ├── diameter_scaling.py        # Diameter scaling calculations
│   └── prediction_aggregator.py   # Prediction selection logic
│
├── simulation/
│   ├── __init__.py
│   └── fairness.py                # Monte Carlo validation
│
└── ui/
    ├── __init__.py
    ├── wood_ui.py                 # Wood configuration UI
    ├── competitor_ui.py           # Competitor selection UI
    ├── handicap_ui.py             # Handicap display UI
    └── tournament_ui.py           # Tournament management UI
```

---

## File Naming Conventions

### Python Files
- `MainProgramV5_2.py` - Main entry point (CamelCase + version)
- `module_name.py` - Modules (snake_case)
- `test_feature.py` - Tests (test_ prefix)

### Documentation Files
- `README.md` - Main project overview (all caps)
- `CLAUDE.md` - AI assistant instructions (all caps)
- `FEATURE_NAME.md` - Feature docs (all caps)
- `ReadMe.md` - User manual (legacy CamelCase)

---

## Recent Cleanup (Jan 4, 2026)

### Deleted (Outdated Developer Artifacts):
- Refactoring documentation (8 files): REFACTORING_COMPLETE.md, REFACTORING_SUMMARY.md, MODULE_REFACTORING_COMPLETE.md, MIGRATION_COMPLETE.md, DIAGNOSIS.md, UH_PREDICTION_ISSUES.md, SCALING_IMPROVEMENTS.md, TIME_DECAY_CONSISTENCY_UPDATE.md
- Old backups: archive/ directory, .ipynb_checkpoints/ directory
- Old scripts: scripts/ directory
- Error file: nul

### Moved to `tests/`:
- test_both_events.py
- test_uh_predictions.py
- test_check_my_work.py
- test_qaa_interpolation.py
- test_monte_carlo_stats.py

### Result:
**Root directory**: 8 essential files (cleaner than ever)
**Docs directory**: 5 current documents (removed 8 historical docs)
**Tests directory**: 5 test scripts (organized)

---

## Quick Navigation

```bash
# View project structure
ls -R

# Read main README
cat README.md

# Browse documentation
cd docs
ls
cat INDEX.md

# Run tests
cd tests
python test_both_events.py

# Start program
python MainProgramV5_2.py
```

---

## Notes

- All markdown files use `.md` extension
- `__pycache__/` auto-generated by Python (can ignore)
- `tournament_state.json` and `multi_tournament_state.json` auto-saved by program

---

**Project Status**: Clean, Organized, Production Ready ✓
