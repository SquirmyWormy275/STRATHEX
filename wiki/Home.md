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

New synthetic delegated sessions can use the [shared managed workspace or CLI](Shared-Managed-Events).
They preserve the retro application and saved competition authority.

## What works today?

**V2** runs locally on Linux and Windows. New **Linux V3** profiles pair STRATHEX
7.4.5 with STRATHMARK 3.0.0rc13 and support review, issue, results, recovery and
later-round learning. They require a separately configured runtime, trained model,
signing authority and independent backups.

Existing 7.4.4/rc12 and 7.4.2/rc7 profiles keep their original runtime and saved competition
identity. Select a new profile through the documented installer workflow; saved
work is never migrated in place. Read the [engine selection guide](Choosing-the-Prediction-Engine) and
[backup guidance](Backups-and-Recovery) before upgrading.

Older V3 numeric previews cannot issue official marks or settle results. The
Windows V7 service is for rehearsal; native Windows compatibility tests do not
establish Windows production qualification.
Read the engine label when choosing V3.

The accuracy changes are available in a separate
[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview).
They have not replaced the competition model.

## For contributors

Use [Development](Development) for setup and tests, [Architecture](Architecture)
for application boundaries, and [Version history](Version-History) for changes.
Detailed specifications and dated release records live in the
[repository docs](https://github.com/SquirmyWormy275/STRATHEX/tree/main/docs).
