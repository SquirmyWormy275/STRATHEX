# FAQ

## Where do I choose V2 or V3?

During single-event setup or at multi-event tournament creation. A tournament's
children inherit the choice. Nothing is selected by default, and the first numeric
operation locks it. See [Engine selection](Choosing-the-Prediction-Engine).

## Can V3 run a full competition?

Yes, with the separately configured Linux competition runtime: STRATHEX 7.4.2 and
STRATHMARK 3.0.0rc7, labeled `LINUX READY`. Older numeric previews cannot issue or
settle, and Windows V7 production qualification remains incomplete.

## Does race day need a network connection?

V2 uses local Python by default. Linux V3 runs in a separate local Python process.
Both need their dependencies and data installed in advance. V2 HTTP and the V7
service are separate configured transports; neither is an automatic fallback.

## Why does V3 show a time but no mark?

It is a seeding forecast. Exact heats and stands must exist before field marks are
calculated. Review, approval and separate issue confirmation come afterward.

## Why do marks change in a final?

Marks belong to a complete field. A final has different competitors, so the engine
recalculates and rebases the field rather than copying earlier marks.

## Do today's results affect later rounds?

V2 keeps its original exclusive date cutoff and excludes same-day results. Linux
V3 freezes evidence within a round, then can learn from valid settled completions
at the next round boundary. Neither uses the old 97/3 tournament blend.

## Does wood quality change V2 predictions?

No. V2 accepts quality as compatibility context but ignores it numerically. Do not
assume V2's inactive-input rules describe every V3 component; see
[Prediction methods](Prediction-Methods).

## Is there an LLM or XGBoost choosing the marks?

There is no hidden STRATHEX-side prediction selector. V2 uses its reviewed
hierarchical core. Linux V3 uses Formula and trained CatBoost ML; its LLM council
is unavailable. Retained local council experiments are diagnostic candidates.

## Have the accuracy changes been implemented?

Yes, in the separate
[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview)
program. They are not enabled in competition predictions. Its historical 2.81% gain
misses the 5% qualification target and has no independent future validation.

## What is the difference between an interval and performance spread?

The forecast interval describes uncertainty in predicted cutting time. Performance
spread describes expected race-to-race variation and drives simulation. They are
not interchangeable.

## What if Excel saves but the database write fails?

Keep the workbook result. Excel is canonical; ResultStore is a separate best-effort
write. Preserve the warning and reconcile the derived store without duplicating rows.

## Can simulation prove that a handicap is fair?

No. It shows outcomes under the supplied predictions and assumptions. Officials
still review the field and apply the governing rules. See [Fairness](Monte-Carlo-Fairness).

## Why did predictions change from v6?

V7 moved numerical prediction to STRATHMARK 2's dated-history core and joint mark
optimizer. The old local XGBoost/LLM selector and QAA scaling are historical.
