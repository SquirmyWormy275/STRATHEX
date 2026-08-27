# Handicap System Explained

STRATHEX delegates prediction and mark arithmetic to the STRATHMARK engine deliberately selected for the competition. V2 remains the production baseline; V3 is an opt-in, readiness-gated rehearsal mechanism until installation-owned production evidence exists.

The choice is made once for a single event or once at tournament creation. Tournament children inherit it. The selected engine is the numeric authority for that scope, and failures never invoke the other engine.

## 1. Evidence cutoff

Every event stores one `prediction_as_of` date. It is an exclusive cutoff: only valid observations dated before it can become evidence. This prevents a resumed or recalculated event from learning from results that did not exist when the event began.
If no event date was entered, the first calculation uses the operator computer's local calendar date and persists it for the event. That matches STRATHEX's local result timestamps and keeps same-event rows excluded across UTC midnight.

Twenty currently tracked historical rows are undated and are therefore excluded by v2. Same-day and future rows are also excluded. Exclusion is a deliberate prior-only rule, not a missing-data fallback.

## 2. Prediction

V2's hierarchical core estimates a predictive distribution for each competitor under one immutable field snapshot. V3 combines reviewed component forecasts under its own signed lifecycle. Either is authoritative only when selected for the competition; a judge may still supply an explicit, separately recorded manual override.

The former STRATHEX numeric LLM, local XGBoost model, expected-error selector, QAA scaling cascade, and 97/3 same-tournament blend are not part of the V2 calculation and are not silently substituted for V3.

STRATHMARK accepts some older context fields for compatibility. In v2, wood quality, same-tournament times, division, heat, and field strength do not change the numeric prediction. The result lists ignored factors so the UI can be honest.

## 3. Two different kinds of uncertainty

The forecast interval answers: “How uncertain is the model about this predicted time?” STRATHEX displays the calibrated interval returned by STRATHMARK.

Performance standard deviation answers: “How much might this competitor vary from race to race?” Monte Carlo simulation uses this spread.

The two values are not interchangeable.

## 4. Forecasting before fields and joint mark optimization

V3 separates prediction-based seeding from handicapping. Its pre-field receipt estimates raw completion time and must say `issued_mark=false`; it cannot be approved, printed, or treated as a mark. Only after STRATHEX creates exact heat membership and stand assignments may V3 assemble complete field-relative marks.

Marks are assigned for the whole field, not by independently rounding each time gap. V2 uses its deterministic common-random-number optimizer over 2,048 posterior samples. V3 uses its reviewed complete-field assembly. Both enforce legal mark limits and return auditable optimizer or receipt evidence.

The legacy rounded-gap method is only a fallback. Any fallback or degraded state must remain visible to the judge.

## 5. Later rounds

Semis and finals recalculate the smaller advancing field because joint marks depend on the competitors in that field. They inherit the root engine choice. V2 reuses the original event cutoff and prior evidence; V3 follows its frozen-round evidence lifecycle. Completed-round times do not silently change the engine or become an undocumented weighting rule.

## 6. Championship and bracket modes

Championship mode uses forecasts from the selected engine, then sets every mark to 3. Its local Monte Carlo count adapts to field size to protect desktop memory.

Bracket mode obtains selected-engine forecasts and seeds fastest predicted time as seed 1. V3 uses a mark-free pre-field forecast for this purpose. Stable IDs and the owning competition authority apply.

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

V3 additionally retains the requested engine separately from returned engine/model evidence, readiness mode, source/contract identity, signed receipt identity, review disposition, and any durable recovery command identity.

That evidence, plus Monte Carlo fairness output, supports review. It is not a guarantee that every competitor has equal win probability.
