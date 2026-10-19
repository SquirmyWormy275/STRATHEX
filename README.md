# STRATHEX

The retro CLI remains the normal entry point. An explicit optional
[shared event mode](docs/MANAGED_EVENTS.md) launches the standalone STRATHMARK
operations or its authenticated workspace against the same persistent event.
Initial managed SB/UH events are synthetic-only; existing V2/V3 saves retain
their original runtime and Excel authority.

STRATHEX is a terminal application for running woodchopping events. It manages
competitors, wood setup, handicap and championship fields, brackets, multi-event
days, results, saves and Excel exports.

[STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) supplies the predicted
cutting times and handicap marks. STRATHEX gives judges the workflow to review
those marks and run the competition.

## Security maintenance

STRATHEX 7.4.6 blocks rehearsal results and schedules from official use, binds
recorded results to reviewed competitor IDs, and checks bounded workbook inputs
before safe atomic writes. Portable installation requires an independent manifest
identity; selected runtime files are checked before execution. Later encrypted recovery verification requires an
independently retained plaintext identity. See the
[latest security notes](docs/SECURITY_CLOUD_FINAL_VALIDATION_2026-10-19.md) and
[7.4.6 release notes](docs/RELEASE_v7.4.6.md) before upgrading.

New installations use STRATHMARK 3.0.0rc14 with the unchanged V2 numerical
contract. Unbound legacy or changed saves stop without being modified or
silently trusted. Keep the original installation and complete backups for saved
competitions, including 7.4.5/rc13, 7.4.4/rc12 and 7.4.2/rc7 profiles. Resume through the
retained profile where compatible; new profiles do not migrate old evidence.
HTTP prediction connections still require verified HTTPS, and the V7 rehearsal
requires an independently provisioned signer identity. Installing code does not
select V3, activate a profile or grant Windows production qualification.

## Start here

You need **Python 3.13**, a UTF-8 terminal and a competition workbook with the
[required sheets](wiki/Data-Model.md). From this repository, on Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Or in Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Launch with explicit paths to your workbook and a directory for saved work:

```bash
strathex --workbook /absolute/path/to/competition.xlsx --data-dir /absolute/path/to/operator-data
```

On Windows, use paths under your account, such as
`C:\Users\YourName\Competitions\competition.xlsx` and a separate
`C:\Users\YourName\STRATHEX-data` directory. Quote paths containing spaces.
A new dedicated data directory is made private. Existing nonempty data directories
are checked without changing their permissions; unsafe shared access stops startup.

The [quick start](wiki/Quick-Start.md) walks through your first event. For a portable
Linux installation with separate release profiles and rollback, use the
[installer guide](docs/PORTABLE_INSTALLATION.md).

## Choose V2 or V3

Each new event or tournament asks you to choose an engine. A tournament's events
and rounds inherit that choice. The first numeric operation locks it; a failure
stops the selected workflow instead of switching engines.

| Choice | What works |
| --- | --- |
| **V2** | Established local prediction and handicap workflow on Linux and Windows. Included with the normal installation. |
| **V3 — LINUX READY** | Full local competition workflow using Formula and trained ML, with review, issue, results, recovery and learning between rounds. Requires separate setup. |
| **V3 — NUMERIC PREVIEW ONLY** | Older preview installation. Proposed times and marks; no official issue or settlement. |
| **V3 — REHEARSAL** | Development service. Windows production qualification is incomplete. |

The new Linux competition pair is **STRATHEX 7.4.6 + STRATHMARK 3.0.0rc14**.
Follow the [Linux V3 setup guide](docs/V3_LINUX_COMPETITION.md) for its separate
Python environment, trained model, signing key and independent backup directory.
The Linux LLM council is unavailable, so fields require explicit degraded or
individual judge review.

Existing **7.4.5/rc13, 7.4.4/rc12 and 7.4.2/rc7 profiles** and other retained competitions keep their original
interpreter, source identity, model, signing authority and saved data. Resume them
with their original profile; a new installation does not migrate an active event.
Windows compatibility checks do not grant Windows V7 production qualification.

A V3 pre-field forecast is forbidden from carrying a mark. Create the actual heats
and stands before calculating field marks, then approve and confirm issue
separately. See [engine selection](wiki/Choosing-the-Prediction-Engine.md).

## Run and save a competition

Set up the event and competitors, create fields, review marks, record official
outcomes and generate later rounds. The [workflow guide](wiki/Tournament-Workflow.md)
explains the order for each engine.

Excel is the canonical result record. JSON saves preserve the competition workflow.
A separate ResultStore write supplies historical evidence; failure there does not
undo a successful workbook write. Back up these records together. V3 also needs
its signing authority, receipts, original model and runtime for recovery.

Use [backups and recovery](wiki/Backups-and-Recovery.md) before moving or upgrading
an installation, and [troubleshooting](wiki/Troubleshooting.md) if work is blocked.

## Accuracy Preview

The [separate preview program](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview)
is implemented and runnable. Its calibration candidate reduced historical average
error from 23.12 to 22.47 seconds, a 2.81% gain. That misses the 5% qualification
target and has no independent future validation. It is **not enabled in competition
predictions** and does not add another choice to the V2/V3 selector.

## More help

- [Wiki](https://github.com/SquirmyWormy275/STRATHEX/wiki): operator guides and explanations.
- [FAQ](wiki/FAQ.md): common questions about engines, data and marks.
- [Current runtime contract](docs/CURRENT_RUNTIME_CONTRACT.md): detailed integration rules.
- [Onboarding](ONBOARDING.md) and [development](wiki/Development.md): contributor setup and isolated tests.
- [Changelog](CHANGELOG.md): release history.

STRATHEX uses the [MIT license](LICENSE). STRATHMARK uses Apache 2.0.
