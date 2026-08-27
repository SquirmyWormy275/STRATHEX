# Quick Start

## Install

Use Python 3.13 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python MainProgramV5_2.py
```

STRATHEX pins the exact STRATHMARK `v2.0.0` release commit from GitHub; no STRATHMARK PyPI distribution is required. Ollama is not required for numeric prediction.

## Run an event

1. Start a single event and deliberately select V2 or an eligible V3 mode. For a multi-event tournament, make this choice once during tournament creation; child events do not choose again.
2. Select the event and configure species, diameter, and quality.
3. Select competitors from the roster.
4. Configure stands and format.
5. Calculate. V2 returns its established mark sheet. V3 first returns signed mark-free forecasts for seeding, then calculates marks after exact heats and stands are generated.
6. Review predicted time, mark, 90% interval, confidence, method, engine state, and warnings.
7. Run local Monte Carlo fairness analysis if desired.
8. Approve marks. V3 offers ordinary green/amber fields as a compact batch and singles out flagged fields for individual disposition.
9. Generate heats or a bracket.
10. Record results; Excel is canonical and ResultStore is best-effort.
11. Save/reload as needed. JSON saves use atomic replacement and backup recovery.
11. Generate later rounds. The advancing field is recalculated using the original cutoff; same-day results are not prediction evidence.

## HTTP demo mode

Start STRATHMARK on loopback with an explicit database path, then set:

```powershell
$env:STRATHMARK_TRANSPORT = "http"
$env:STRATHMARK_API_URL = "http://127.0.0.1:8000"
python MainProgramV5_2.py
```

A version mismatch or API failure stops the calculation visibly. Neither transport nor engine silently falls back.
