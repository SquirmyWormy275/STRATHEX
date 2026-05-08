# STRATHEX

**A CLI tournament management system for Australian-style woodchopping competitions, built on the STRATHMARK handicap engine.**

A world-champion axeman cuts a 300mm Standing Block in about 25 seconds. A skilled amateur takes 60. Run them in the same heat without a handicap and the amateur has zero chance, so the amateur stays home and the tournament dies. Handicapping fixes this by delaying faster competitors' starts so everyone should finish together. STRATHEX predicts each competitor's cutting time as accurately as possible, applies the AAA-compliant mark formula, and validates fairness with 2 million Monte Carlo races before a single axe lands.

In production testing the system holds the simulated finish-time spread between **0.3 and 0.8 seconds across all competitors** against a target of <1.0s, and the win-rate spread under 2%. It does this by combining a time-decayed statistical baseline, an XGBoost machine-learning model trained per event, and an optional Ollama LLM that reasons over wood quality and recent form. As of V6.0 the calculation engine lives in a separate pip-installable package, **[STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK)**, which any other tournament software can depend on without inheriting STRATHEX's CLI.

## My role

Solo developer. I designed and built STRATHEX end-to-end: the CLI, the prediction stack, the Monte Carlo validator, the multi-round and multi-event tournament workflows, the Excel ingest pipeline, the GitHub Actions CI matrix, and the V6.0 STRATHMARK extraction that split the calculation engine into its own repo. STRATHMARK is also solo work and ships its own 44-file test suite (~707 tests) independently. Australian competition rules and the QAA diameter scaling tables are external sources cited in the wiki.

## Tech stack

**Runtime:** Python 3.13, pandas, numpy, openpyxl, scikit-learn, xgboost, lightgbm, matplotlib, requests.
**Engine:** [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) (pip-installed direct from GitHub via `pyproject.toml`), exposing `HandicapCalculator`, `run_monte_carlo_simulation`, `get_ai_assessment_of_handicaps`, and a `ResultStore` SQLite layer.
**LLM (optional):** Ollama with the `qwen2.5:7b` model running locally.
**Build / quality:** hatchling, ruff (lint + format), pytest with coverage. CI runs on Ubuntu and Windows for every push and pull request.
**Persistence:** Excel (judge-portable) and SQLite at `~/.strathmark/results.db` (dual-write, idempotent migration on startup).

## Key features

- **Multi-round tournaments:** heats → semi-finals → finals with automatic advancement, per-round result entry, and 97% same-wood tournament weighting in later rounds.
- **Multi-event tournament days:** five or six independent events on one card, each with its own wood, roster, format, payouts, and event type (Handicap or Championship).
- **Bracket tournaments:** single and double elimination with AI-suggested seeding.
- **Championship Race Simulator:** equal-start race outcome predictions with 2M Monte Carlo iterations and AI commentary, used as a fun analytical tool separate from handicap fairness.
- **Three prediction methods:** statistical baseline with QAA diameter scaling, XGBoost (separate models for Standing Block and Underhand), and an optional LLM that adjusts for wood quality and recent form. Selection uses expected-error scoring rather than a fixed cascade.
- **Monte Carlo fairness validation:** default 250,000 race iterations, validating ±3s absolute variance per competitor (deliberately not proportional variance, which would advantage faster competitors).
- **AAA / QAA rule compliance:** 3-second minimum mark, 180-second time limit, nearest-second rounding, all enforced as frozen-dataclass constants in `config.py`.

## Architecture

```text
STRATHEX (this repo)                     STRATHMARK (sister repo)
+------------------------------+         +------------------------------+
| MainProgramV5_2.py           |         | calculator.py                |
|   tournament loop, menus     |         |   HandicapCalculator         |
| woodchopping/                |         | predictor.py                 |
|   ui/      Excel I/O, judge  |  pip    |   prediction cascade         |
|   data/    DataFrame plumbing| ------> | variance.py                  |
|   handicaps/  thin wrappers  |  via    |   Monte Carlo (250k - 2M)    |
|   simulation/ proxy modules  | git+    | fairness.py                  |
|   strathmark_adapter.py *    | https   |   AI fairness assessment     |
+------------------------------+         | store.py + migrations/       |
                                         |   SQLite ResultStore         |
                                         | api.py                       |
                                         |   FastAPI HTTP endpoints     |
                                         +------------------------------+
* the only file in STRATHEX that imports strathmark
```

Full module map and design-decision rationale: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [wiki/Architecture](wiki/Architecture.md).

The clean adapter boundary means STRATHMARK has zero imports from STRATHEX. The library is Apache 2.0 licensed, and other tournament software can install it directly from GitHub today (`pip install git+https://github.com/SquirmyWormy275/STRATHMARK.git`); PyPI publication is pending the v1.0.0 release, after which the standard `pip install strathmark` form will work.

## Quickstart

```powershell
# Clone and install. STRATHMARK is pulled automatically as a Git dependency.
git clone https://github.com/SquirmyWormy275/STRATHEX.git
cd STRATHEX
pip install -e ".[dev]"

# Run the CLI.
python MainProgramV5_2.py

# Run the test suite (skips Ollama-dependent tests, same as CI).
pytest tests/ -v -m "not ollama" --cov=woodchopping
```

**Prerequisites:** Python 3.13+, an Excel file at `woodchopping_clean.xlsx` (a sample is included), and optionally a local Ollama instance running `qwen2.5:7b` if you want the LLM predictor.

For development against a live STRATHMARK checkout:

```powershell
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK
```

Edits to STRATHMARK source then take effect on the next STRATHEX run with no rebuild step.

## What it looks like

Real CLI banner from the tournament control screen:

```text
======================================================================
                     TOURNAMENT CONTROL SYSTEM
                  Spring Open 2026  ·  5 events
----------------------------------------------------------------------
  1. Configure event (wood, format, stands, type)
  2. Select competitors
  3. Calculate handicap marks
  4. View Monte Carlo fairness analysis
  5. Generate next round
  6. Record results
  7. Approve and advance
  8. Tournament summary
  9. Save and exit
======================================================================
```

The system is plain ASCII by design: judges run it on a single laptop in a sawdust pile and the retro aesthetic signals "field-ready, low-friction" rather than "demo software."

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): system architecture, data flow, failure modes, what I would do differently
- [docs/CASE_STUDY.md](docs/CASE_STUDY.md): design decisions and what shipped, with the rationale for each
- [docs/SYSTEM_STATUS.md](docs/SYSTEM_STATUS.md): current capabilities, ML model audit, fairness metrics
- [docs/PROMPT_ENGINEERING_GUIDELINES.md](docs/PROMPT_ENGINEERING_GUIDELINES.md): LLM prompt discipline and version history
- [docs/solutions/](docs/solutions/): 13 documented solutions to past problems, indexed by `module`, `tags`, `problem_type`
- [wiki/](wiki/): 17-page judge-facing wiki (handicap explanation, AAA/QAA rule compliance, FAQ, troubleshooting)
- **CI:** [.github/workflows/ci.yml](.github/workflows/ci.yml) runs ruff lint + pytest on Ubuntu and Windows + a build-and-import verification step

## Project context

STRATHEX is a personal project showcasing both the prototype application and the STRATHMARK engine extraction. It targets two audiences: hiring managers evaluating my work, and US woodchopping show runners exploring Australian-style handicap tournaments. The handicap methodology is grounded in 150+ years of empirical Australian data via the Queensland Axemen's Association scaling tables. For a deeper system explanation written for tournament organizers, see the [wiki Home page](wiki/Home.md).

## About the author

**Alex Kaper.** MIS graduate (May 2026) from the University of Montana College of Business.

- LinkedIn: [linkedin.com/in/alex-kaper](https://linkedin.com/in/alex-kaper)
- Email: [alex.j.kaper@gmail.com](mailto:alex.j.kaper@gmail.com)

## License

[MIT](LICENSE)

---

*Last updated: May 2026 — V6.0*
