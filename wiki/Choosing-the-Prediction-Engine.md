# Choose V2 or V3

Choose the engine when you create the competition. Nothing is selected by default.

- **Single event: choose once during event setup.**
- **Multi-event tournament: choose once at tournament creation.** Child events
  and rounds inherit the choice and never show their own selector.

The first numeric operation locks the choice. There is no fallback between engines.
A later competition can use a different engine; an existing one must resume with
its selected engine and original installation.

## Read the V3 label

| Label | What it means |
| --- | --- |
| `LINUX READY` | Configured local Linux competition runtime with Formula and trained ML. Supports review, issue, results, settlement and recovery. |
| `NUMERIC PREVIEW ONLY` | Older preview profile. Can propose times and marks, but cannot issue or settle a competition. |
| `REHEARSAL` | Development service. Does not establish Windows production eligibility. |

V2 is the established local engine on Linux and Windows. The full Linux V3 profile
requires STRATHMARK 3.0.0rc7 with STRATHEX 7.4.2, a trained model, signing key and
independent backups. Use the
[Linux setup guide](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_LINUX_COMPETITION.md).
Windows V7 production qualification remains incomplete.

## Why are there times but no marks yet?

The V3 pre-field forecast contains no mark. It supplies cutting-time predictions
for seeding before exact heats and stands exist.

Generate the actual heats and stands, then calculate the complete field's proposed
marks. Review and approve them, then confirm **Issue these approved marks now?**
separately. An approved but unissued field cannot be printed as an official sheet
or accept results.

Linux V3's LLM council is unavailable. Fields therefore require explicit degraded
or individual review. Formula/ML counterfactual disagreement of five or more marks
requires individual review.

## What happens after a heat?

V2 keeps its original exclusive date cutoff and excludes same-day results. Linux
V3 keeps all heats in a round on frozen evidence, then uses valid settled results
at the next round boundary. It recalculates the advancing field together; marks
are not copied from a previous heat.

## Resuming saved work

Keep the original source, trained model, authority key and runtime. An upgrade can
block an old V3 scope if those no longer match. Restore the original profile rather
than switching engines or creating a new key. See [Recovery](Backups-and-Recovery).

[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview)
is a separate program. It does not replace either competition engine.
