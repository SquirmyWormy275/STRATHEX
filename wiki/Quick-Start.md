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

1. Select the event and configure species, diameter, and quality.
2. Select competitors from the roster.
3. Configure stands and format.
4. Calculate handicaps. STRATHEX persists one exclusive evidence cutoff.
5. Review predicted time, mark, 90% interval, confidence, method, engine state, and warnings.
6. Run local Monte Carlo fairness analysis if desired.
7. Approve or explicitly adjust marks.
8. Generate heats or a bracket.
9. Record results; Excel is canonical and ResultStore is best-effort.
10. Save/reload as needed. JSON saves use atomic replacement and backup recovery.
11. Generate later rounds. The advancing field is recalculated using the original cutoff; same-day results are not prediction evidence.

## HTTP demo mode

Start STRATHMARK on loopback with an explicit database path, then set:

```powershell
$env:STRATHMARK_TRANSPORT = "http"
$env:STRATHMARK_API_URL = "http://127.0.0.1:8000"
python MainProgramV5_2.py
```

A version mismatch or API failure stops the calculation visibly. Remote endpoints require HTTPS.
