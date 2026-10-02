# STRATHEX onboarding

STRATHEX 7.1 is the portable judge-facing terminal application. V2 remains its production baseline, pinned to STRATHMARK 2.0.0 at `a231ad65fe82317516cc82a282761d73adb0c0e3`. V3 uses a separate authenticated V7 service and remains rehearsal-only.

Read the [handicap foundations](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/wiki/Handicap-Mark-Math.md), [README](README.md), [current runtime contract](docs/CURRENT_RUNTIME_CONTRACT.md), [architecture](docs/ARCHITECTURE.md), and [V3 rehearsal setup](docs/V3_REHEARSAL.md).

Install Python 3.13, then `python -m pip install -e ".[dev,api-test]"`. Linux and Windows share the same source and command: `strathex --workbook /absolute/path/to/workbook.xlsx --data-dir /absolute/path/to/operator-data`. On Windows, use Windows absolute paths. The workbook must exist and include Competitor, Wood, and Results sheets. Data-directory defaults can be overridden by the explicit STRATHMARK/STRATHEX environment variables documented in the runbook.

The legacy `python MainProgramV5_2.py` entry remains supported. It opens the configured workbook at import time, initializes ResultStore, and starts its interactive loop. Use the new launcher to select paths before those imports. Keep workbook and data backups together.

For tests, use a fresh temporary directory, export `STRATHMARK_TEST_DB=1`, and assign unique `STRATHMARK_DB_PATH`, `STRATHMARK_V3_DB_PATH`, `STRATHEX_PREDICTION_AUTHORITY_DB`, and `STRATHEX_V3_COMMAND_DB` paths. Run pytest with an explicit `--basetemp` and `-p no:cacheprovider`. Existing tests use synthetic data; historical benchmark scripts are excluded from release collection.

Run `ruff check .`, `ruff format --check .`, `python scripts/check_docs.py`, `python -m build`, then `python scripts/smoke_installed_app.py --wheel dist/strathex-7.1.0-py3-none-any.whl`. The installed smoke starts and exits the actual terminal app with a generated workbook outside the checkout. It opens no live competition data.
