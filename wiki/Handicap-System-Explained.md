# Handicap System Explained

## Fixed evidence

An event stores one exclusive `prediction_as_of` date. Only valid observations before that date can become v2 evidence. This makes recalculation and resume reproducible.
If no event date was entered, STRATHEX persists the operator computer's local calendar date on the first calculation. This matches locally recorded result dates and prevents same-event rows from entering later-round predictions after UTC midnight.

## Prediction and uncertainty

STRATHMARK's hierarchical core predicts the field under one immutable model snapshot. The 90% forecast interval describes model uncertainty. Performance standard deviation describes race-to-race variation and drives simulation. They are distinct.

## Marks

STRATHMARK assigns legal marks jointly for the whole field with a deterministic optimizer. It does not simply round each independent predicted-time gap. Optimizer metadata, warnings, and degraded state are visible.

## Later rounds

An advancing field is recalculated because field composition changes mark optimization. It uses the original cutoff. Same-day heat times are judge reference only and receive no special weight.

## Compatibility inputs

Wood quality and tournament context are stored and sent where supported but do not alter v2 numerics. Numeric LLM, local XGBoost selection, and QAA scaling are not live methods.

Judges can still make explicit manual adjustments after reviewing the evidence.
