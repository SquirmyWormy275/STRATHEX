# STRATHEX

STRATHEX helps judges set up and run woodchopping competitions. It is a terminal
application with menus for events, tournaments, competitors, results and exports.
[STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK/wiki) calculates the
predicted cutting times and handicap marks.

## Find what you need

| I want to… | Start here |
| --- | --- |
| Install and run my first event | [Quick start](Quick-Start) |
| Choose V2 or V3 | [Engine selection](Choosing-the-Prediction-Engine) |
| Run heats, enter results and advance | [Tournament workflow](Tournament-Workflow) |
| Run several events in one day | [Multi-event tournaments](Multi-Event-Tournaments) |
| Run a bracket | [Brackets](Bracket-Tournaments) |
| Prepare my workbook | [Workbook and data](Data-Model) |
| Understand handicap marks | [Handicaps explained](Handicap-System-Explained) |
| Back up or recover saved work | [Backups and recovery](Backups-and-Recovery) |
| Fix a blocked workflow | [Troubleshooting](Troubleshooting) |
| Find a quick answer | [FAQ](FAQ) |

## What works today?

**V2** runs locally on Linux and Windows. **Linux V3**, with STRATHEX 7.4.2 and
STRATHMARK 3.0.0rc7, supports review, issue, results, recovery and later-round
learning. It requires a separately configured runtime and trained model.

Older V3 numeric previews cannot issue official marks or settle results. The
Windows V7 service is for rehearsal; Windows production qualification is incomplete.
Read the engine label when choosing V3.

The accuracy changes are available in a separate
[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview).
They have not replaced the competition model.

## For contributors

Use [Development](Development) for setup and tests, [Architecture](Architecture)
for application boundaries, and [Version history](Version-History) for changes.
Detailed specifications and dated release records live in the
[repository docs](https://github.com/SquirmyWormy275/STRATHEX/tree/main/docs).
