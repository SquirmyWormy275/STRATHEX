# STRATHEX 7

STRATHEX is the judge-facing woodchopping tournament application. It manages rosters, wood setup, handicap and championship fields, brackets, multi-event days, result entry, autosave, and Excel exports. Numeric prediction and mark assignment are owned by [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK).

## Prediction-engine choice

Every new competition begins with no prediction engine selected. The judge must deliberately choose STRATHMARK V2 or V3:

- a single event chooses once during event setup;
- a multi-event tournament chooses once at tournament creation, and every child event and round inherits it;
- no child event can override the tournament choice;
- the choice locks at the first numeric operation;
- an outage or incompatible response blocks work rather than calling the other engine.

V2 remains the established production baseline. V3 is selectable only when its authenticated loopback service proves an exact reviewed contract and source identity. The currently supported V3 path is rehearsal-only unless installation-owned production evidence says otherwise; selecting it does not enable a global V3 cutover.

V3 uses a two-stage workflow. A signed pre-field forecast supplies raw-time estimates for seeding before heats exist and is forbidden from carrying a mark. After STRATHEX creates exact heats and stand assignments, V3 assembles the complete field-relative mark sheet. See [Choosing the Prediction Engine](wiki/Choosing-the-Prediction-Engine.md).

## V2 production baseline

STRATHEX 7 is integrated with the [STRATHMARK 2.0.0 release](https://github.com/SquirmyWormy275/STRATHMARK/releases/tag/v2.0.0) at exact commit `a231ad65fe82317516cc82a282761d73adb0c0e3`. STRATHMARK 2.0.0 is distributed through GitHub rather than PyPI, so the Git dependency remains commit-pinned for reproducibility.

The live calculation contract is:

- one prior-only hierarchical prediction core;
- stable competitor IDs and dated history;
- one persisted, exclusive `prediction_as_of` cutoff per event;
- calibrated forecast intervals, separate race-performance standard deviation, and explicit provenance;
- deterministic joint optimization of legal handicap marks;
- manual operator adjustments as explicit authority;
- no numeric LLM prediction, no local XGBoost selection cascade, and no 97/3 same-tournament reweighting;
- wood quality and same-tournament times retained as compatibility context but ignored by v2 numerics.

V2-selected bracket seeding, championship predictions, single-event handicaps, and multi-event handicaps use this boundary unchanged.

## Transports

Direct Python is the default and remains usable without a race-day network:

```powershell
python MainProgramV5_2.py
```

The demo can explicitly call STRATHMARK's stateless FastAPI field endpoint:

```powershell
# In the STRATHMARK checkout
$env:STRATHMARK_DB_PATH = "C:\path\to\strathmark-demo.db"
uvicorn strathmark.api:app --host 127.0.0.1 --port 8000

# In the STRATHEX shell
$env:STRATHMARK_TRANSPORT = "http"
$env:STRATHMARK_API_URL = "http://127.0.0.1:8000"
python MainProgramV5_2.py
```

HTTP mode checks the audited 2.0.0 `/calculate` OpenAPI request/response shape and every result's required audit metadata. It never silently falls back to Python or follows redirects, and response bodies are size-bounded. Plaintext HTTP is accepted only on loopback; remote endpoints require HTTPS, and configured URLs cannot contain credentials, paths, queries, or fragments. `POST /calculate` is stateless and unauthenticated, so do not expose it publicly without a deliberate security boundary.

## Persistence

Excel is the judge-canonical result record. STRATHEX then attempts a best-effort write to STRATHMARK ResultStore. These are two separate writes, not one cross-store atomic transaction. A ResultStore failure does not roll back a successful Excel write.

Single-event and multi-event JSON state use validated temporary files, atomic replacement, and rolling backups. Before STRATHMARK v2 first opens an existing ResultStore, STRATHEX creates a one-time `.pre-v2.bak` copy. New result writes include a stable competition ID and event date.

ResultStore history, STRATHMARK PredictionLedger receipts, and the public stateless calculation endpoint are distinct facilities. STRATHEX 7 uses ResultStore history locally and does not write trusted PredictionLedger receipts through `/ledger/calculate`.

## Install and test

Requirements: Python 3.13+, Windows or another terminal with Unicode support, and the supplied workbook schema.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,api-test]"
```

Tests must always use a disposable STRATHMARK database:

```powershell
$env:STRATHMARK_TEST_DB = "1"
$env:STRATHMARK_DB_PATH = "$env:TEMP\strathex-tests.db"
python -m pytest -p no:cacheprovider --basetemp "$env:TEMP\strathex-pytest"
python -m ruff check --no-cache .
python -m ruff format --check --no-cache .
```

The cache flags are needed only in restricted nested worktrees. Never point tests at the production ResultStore or workbook.

## Documentation

- [Current runtime contract](docs/CURRENT_RUNTIME_CONTRACT.md)
- [Choosing the prediction engine](wiki/Choosing-the-Prediction-Engine.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Handicap system](docs/HANDICAP_SYSTEM_EXPLAINED.md)
- [STRATHMARK 2 migration decision](docs/STRATHMARK_2_COMPATIBILITY_EVALUATION.md)
- [STRATHEX 7 release notes](docs/RELEASE_v7.0.0.md)
- [Documentation index](docs/INDEX.md)
- [Versioned wiki source](wiki/README.md)

Dated v6.0.1 release and audit documents are preserved as historical evidence. Baseline/XGBoost/Ollama, QAA interpolation, and prompt-engineering reports are historical and do not describe the live v7 runtime.

## License

STRATHEX is MIT licensed. STRATHMARK is Apache 2.0 licensed.
