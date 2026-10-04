# Start your first event

Use this guide for a V2 event. If you want Linux V3, complete the separate
[Linux V3 setup](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_LINUX_COMPETITION.md)
first, then follow the [V3 workflow](Tournament-Workflow).

## 1. Install STRATHEX

You need Python 3.13 and Git. Download this repository:

```bash
git clone https://github.com/SquirmyWormy275/STRATHEX.git
cd STRATHEX
```

Create and activate the environment on Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Or in Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Then install:

```bash
python -m pip install -e .
```

The installation includes the reviewed STRATHMARK V2 source dependency. You do
not need Ollama or a separate PyPI installation for V2 predictions.

## 2. Select your data paths

Keep a backup of your workbook before first use. It needs the `Competitor`, `wood`
and `Results` sheets described in [Workbook and data](Data-Model).

Linux example:

```bash
strathex --workbook /home/you/Competition/competition.xlsx --data-dir /home/you/Competition/operator-data
```

Windows example:

```powershell
strathex --workbook "C:\Competition\competition.xlsx" --data-dir "C:\Competition\operator-data"
```

Replace those paths with your own. The data directory holds saves and local
competition records. Explicit environment settings can take precedence; see
[Troubleshooting](Troubleshooting) if the application opens unexpected data.

## 3. Create the event

1. Choose **Design an Event (Single Event)** from the main menu.
2. Deliberately choose **V2** when asked for the prediction engine.
3. Select the event, species, diameter, quality, stands and format.
4. Select competitors from the roster. Check names and stable IDs.
5. Calculate and review the predicted times, marks, intervals and warnings.
6. Apply any authorized V2 adjustments explicitly, then generate heats.
7. Check the actual start sheet before running the race.

A smaller mark starts earlier. The predicted time is the competitor's raw cutting
time, not their finish time measured from the starter's first count.
[Handicaps explained](Handicap-System-Explained) has a worked example.

## 4. Record results and continue

Enter raw cutting times and official outcomes through the event workflow. Save
before closing. Use **Load Previous Event/Tournament** to resume.

Select advancing competitors and calculate the next field. V2 retains the event's
original date cutoff, so today's results are recorded but do not change its
same-day predictions. Linux V3 handles later-round learning differently.

For payouts, multiple rounds, brackets and V3 approval/issue, continue with
[Tournament workflow](Tournament-Workflow). Keep [backups](Backups-and-Recovery)
for the workbook and saved state together.
