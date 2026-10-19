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

V2 is the established local engine on Linux and Windows. New full Linux V3 profiles
use STRATHMARK 3.0.0rc13 with STRATHEX 7.4.5, a trained model, signing key and
independent backups. Installing this package pair does not configure or activate
a local profile. Use the
[Linux setup guide](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_LINUX_COMPETITION.md).
Native Windows compatibility tests do not grant Windows V7 production eligibility;
its CNG qualification remains separate.

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

Keep the original source, trained model, authority key and runtime. Existing
7.4.4/rc12 and 7.4.2/rc7 profiles retain their exact original installations; the rc13 pair is for new
profiles. The adapter accepts only its explicitly reviewed implementations, and a saved
scope still requires its original recorded identity. Resume the original profile instead
of replacing its runtime, switching engines or creating a new key. See
[Recovery](Backups-and-Recovery).

[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview)
is a separate program. It does not replace either competition engine.
