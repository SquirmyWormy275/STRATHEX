# Prediction methods

STRATHEX sends calculations to the STRATHMARK engine chosen for the competition.
It does not choose between hidden local predictors.

## Active engines

| Engine | How it predicts |
| --- | --- |
| V2 | A hierarchical model combines prior-only personal history with population estimates, calibrated uncertainty and joint mark optimization. |
| Linux V3 competition | Independent Formula and trained CatBoost ML forecasts, capability updates and earned component weights, followed by complete-field mark calculation. |

Linux V3's LLM council is unavailable. The wider three-member council design and
local diagnostic experiments are not an active numeric council in this profile.
Older preview and Windows rehearsal installations have their own limitations;
see [Engine selection](Choosing-the-Prediction-Engine).

## History and wood

V2 sends stable competitor IDs and valid dated history under one exclusive cutoff.
Undated, same-day, future and invalid observations are excluded. Quality and
same-tournament weighting are accepted but do not change V2 numbers.

V3 freezes evidence for all fields in a round. Valid settled results become eligible
at the next round boundary. An advancing field is reconstructed and recalculated,
rather than inheriting individual marks.

## What to review

A prediction includes more than a time: uncertainty, performance spread, cutoff,
engine/model versions, warnings, degraded state and provenance. V2 returns optimizer
evidence. V3 retains component forecasts and signed field, review, issue and result
receipts.

An explicit V2 manual override remains a judge decision. It is not evidence that
an experimental model has been promoted.

## What is historical or experimental?

The STRATHEX-side baseline/XGBoost/Ollama selector and QAA interpolation are retired
from live v7 prediction. Old reports remain as dated records.

[Accuracy Preview](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Accuracy-Preview)
is implemented separately. Its candidate is not enabled in competition predictions.
For numerical details, read [V2](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Prediction-Engine-V2)
or [V3](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Prediction-Engine-V3).
