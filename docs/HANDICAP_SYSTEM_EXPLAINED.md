# Handicap System Explained

STRATHEX 7 delegates prediction and mark arithmetic to STRATHMARK 2.0. This page describes the live system.

## 1. Evidence cutoff

Every event stores one `prediction_as_of` date. It is an exclusive cutoff: only valid observations dated before it can become evidence. This prevents a resumed or recalculated event from learning from results that did not exist when the event began.

Twenty currently tracked historical rows are undated and are therefore excluded by v2. Same-day and future rows are also excluded. Exclusion is a deliberate prior-only rule, not a missing-data fallback.

## 2. Prediction

STRATHMARK's hierarchical core estimates a predictive distribution for each competitor under one immutable field snapshot. The live 2.0 model is the authority unless a judge supplies an explicit manual override.

The former STRATHEX numeric LLM, local XGBoost model, expected-error selector, QAA scaling cascade, and 97/3 same-tournament blend are not part of the v7 calculation.

STRATHMARK accepts some older context fields for compatibility. In v2, wood quality, same-tournament times, division, heat, and field strength do not change the numeric prediction. The result lists ignored factors so the UI can be honest.

## 3. Two different kinds of uncertainty

The forecast interval answers: “How uncertain is the model about this predicted time?” STRATHEX displays the calibrated interval returned by STRATHMARK.

Performance standard deviation answers: “How much might this competitor vary from race to race?” Monte Carlo simulation uses this spread.

The two values are not interchangeable.

## 4. Joint mark optimization

Marks are assigned for the whole field, not by independently rounding each time gap. STRATHMARK v2 uses a deterministic common-random-number optimizer over 2,048 posterior samples and enforces mark limits. Its optimizer name and metadata are returned with the result.

The legacy rounded-gap method is only a fallback. Any fallback or degraded state must remain visible to the judge.

## 5. Later rounds

Semis and finals recalculate the smaller advancing field because joint marks depend on the competitors in that field. They reuse the original event cutoff and prior evidence. Completed-round times are shown for reference but do not receive special prediction weight.

## 6. Championship and bracket modes

Championship mode groups competitors that share target wood/history context, uses v2 predicted raw times and performance spread, then sets every mark to 3. Its local Monte Carlo count adapts to field size to protect desktop memory.

Bracket mode obtains one v2 field calculation and seeds fastest predicted time as seed 1. Stable IDs and the same cutoff contract apply.

## 7. Manual authority

A judge can adjust marks after seeing the calculation. Manual action is explicit, separately recorded, and never disguised as a model result. When STRATHMARK itself receives a manual time override, the method and provenance identify it as manual.

## 8. What the judge sees

For each competitor STRATHEX retains:

- name and stable ID;
- predicted time and mark;
- method and confidence;
- calibrated interval;
- performance standard deviation;
- engine, model, and calibration versions;
- evidence cutoff;
- optimizer and metadata;
- warnings and degraded state;
- provenance and ignored factors.

That evidence, plus Monte Carlo fairness output, supports review. It is not a guarantee that every competitor has equal win probability.
