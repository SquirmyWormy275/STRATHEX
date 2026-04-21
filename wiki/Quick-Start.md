# Quick Start

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.13+ | The code uses modern typing and `match`/`case`; 3.12 and below are not supported |
| Excel file | `woodchopping.xlsx` in the project root. Sheets: `Competitor`, `wood`, `Results`. See [Data Model](Data-Model) |
| Ollama (optional) | Local LLM server at `http://localhost:11434` running `qwen2.5:7b` for AI predictions and fairness narration. Everything works without it — the system falls back to the ML and baseline predictors |
| Windows / macOS / Linux | Tested daily on Windows 11 and Ubuntu (CI matrix) |

## Install

```bash
git clone https://github.com/SquirmyWormy275/STRATHEX.git
cd STRATHEX
pip install -e ".[dev]"        # Core + ML + dev tooling. Pulls STRATHMARK from GitHub.
```

For the optional LLM predictor layer:
```bash
pip install -e ".[dev,llm]"    # Adds the Ollama Python client (HTTP works without it too)
```

All runtime and dev dependencies live in [`pyproject.toml`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/pyproject.toml). There is **no** `requirements.txt`.

## Editable STRATHMARK (for engine developers)

By default `pip install -e .` pulls [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) from its `main` branch. If you're actively developing the engine, clone it alongside STRATHEX and reinstall as editable:

```bash
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK
```

Python now reads STRATHMARK source directly — any change to the engine is live on the next STRATHEX run, no re-install required.

## Run the program

```bash
python MainProgramV5_2.py
```

You should see:

```
╔════════════════════════════════════════════════════════════════════╗
║              WOODCHOPPING HANDICAP SYSTEM V6.0                     ║
║                                                                    ║
║        Data-driven handicaps · STRATHMARK engine · Python 3.13+    ║
╚════════════════════════════════════════════════════════════════════╝

1. Design an Event (Single Event Tournament)
2. Design a Tournament (Multiple Events)
3. Championship Race Simulator
4. View Competitor Dashboard
5. Add/Edit/Remove Competitors from Master Roster
6. Load Previous Event/Tournament
7. Reload Roster from Excel
8. How Does This System Work?
9. Exit
```

## First tournament — the five-minute walkthrough

1. **Pick option 1** (Single Event Tournament).
2. Configure wood: species, diameter (mm), quality (0–10). The system warns if the diameter is high-variance; see [QAA scaling](Handicap-System-Explained#diameter-scaling).
3. Configure tournament: number of stands, format (heats→finals or heats→semis→finals), event name.
4. Select competitors. The roster filters by event history — anyone with fewer than 3 recorded results for this event is blocked (see [sparse-data rules](Handicap-System-Explained#sparse-data-validation)).
5. **Calculate handicaps.** STRATHEX picks the best prediction method per competitor and prints a three-column table: Baseline · ML · LLM, with the selected value highlighted.
6. (Optional) Run the **Monte Carlo simulation** to validate fairness. Target is a win-rate spread under 2%.
7. **Approve** marks. You can manually override any mark before generating the schedule.
8. **Generate heats.** Record each finish time. Pick advancers.
9. **Generate next round.** Semis/finals use today's heat results at 97% weight — see [tournament weighting](Handicap-System-Explained#tournament-result-weighting).
10. Done. Results append to the `Results` sheet in `woodchopping.xlsx` and the STRATHMARK SQLite ResultStore.

## Verify the install

```bash
python -c "from woodchopping.handicaps.calculator import calculate_ai_enhanced_handicaps; print('OK')"
pytest tests/ -v -m "not ollama" --cov=woodchopping
```

CI runs the same checks on every push (Ubuntu + Windows). See [Development](Development) for the full loop.

## Upgrade path from V5.2

If you're running the legacy pure-Python branch (`v5.2-legacy`), the jump to `main` (V6.0) is automatic: STRATHMARK is a transparent dependency. Your Excel file is unchanged; on first startup, STRATHEX migrates the `Results` sheet into SQLite (idempotent, duplicates skipped). Nothing to do.
