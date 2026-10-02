# Quick Start

## Available runtime profiles

STRATHEX 7.2.0 preserves V2 production operation and offers two explicitly configured V3 rehearsal profiles. The [Linux numeric candidate](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_REHEARSAL.md) runs real Formula, trained ML, pooling, and exact-field optimization through a separate Python 3.13 subprocess. Its mark-free seeding forecasts and proposed marks are unissued previews. Saved selection binds the implementation, Formula manifest, model bundle, and frozen workbook; field previews also bind revision and stand order. It cannot approve, issue, record official results, export official schedules, settle, or learn at the next round.

The authenticated V7 profile uses signed lifecycle receipts and requires full backend composition and installation qualification. Its lifecycle behavior described below applies only when that full runtime is configured and ready. The checked-in transport rehearsal uses fixtures and does not prove a real numeric lifecycle. A judge deliberately selects V2 or an available V3 profile once per competition root; failures stop the selected workflow.

## Install

Use Python 3.13 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python MainProgramV5_2.py
```

STRATHEX pins the exact STRATHMARK `v2.0.0` release commit from GitHub; no STRATHMARK PyPI distribution is required. Ollama is not required for numeric prediction.

## Run an event with V2 or the full authenticated V7 runtime

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
12. Generate later rounds. V2 retains its original exclusive cutoff and excludes same-day results. V3 keeps same-round epochs frozen and admits settled completions at a later-round boundary, then rebuilds and rebases the complete field.

## HTTP demo mode

Start STRATHMARK on loopback with an explicit database path, then set:

```powershell
$env:STRATHMARK_TRANSPORT = "http"
$env:STRATHMARK_API_URL = "http://127.0.0.1:8000"
python MainProgramV5_2.py
```

A version mismatch or API failure stops the calculation visibly. Neither transport nor engine silently falls back.

## Linux numeric previews

Follow the linked V3 runbook to install the separate V3 interpreter and a verified private candidate bundle, then pass `--local-v3-python` and `--local-v3-ml-bundle` with the workbook/data paths. Select V3 during event creation. Review numeric previews and save/reload; official result, approval, issue, and schedule workflows are blocked for this profile.

## Linux

Install in a Python 3.13 virtual environment, then run `strathex --workbook /absolute/path/to/workbook.xlsx --data-dir /absolute/path/to/operator-data`. Use `source .venv/bin/activate` to activate the Linux environment. See the [Linux setup and rehearsal runbook](https://github.com/SquirmyWormy275/STRATHEX/blob/main/ONBOARDING.md).
