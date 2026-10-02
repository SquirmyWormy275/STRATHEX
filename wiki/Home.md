# STRATHEX 7.2.1

STRATHEX is the terminal application judges use to run woodchopping events. It handles rosters, wood setup, handicap and championship fields, brackets, multi-event days, schedules, results, autosave, and exports.

Numeric prediction and handicap marks come from the STRATHMARK engine deliberately selected for that competition. V2 remains the production baseline. V3 can use the authenticated V7 service or the explicit Linux numeric candidate. The candidate runs actual Formula + trained ML and optimization, displays NUMERIC PREVIEW ONLY, and cannot approve, issue, settle, or learn from later rounds.

STRATHEX 7.2.1 pins its V3 rehearsal service to security-maintained source `8a1d40aa5645715f9ab876d0517b64c36602a77e`. Linux and Windows CI exercise installed consumer/service wheels over loopback, including approval/issue separation and exact settlement recovery after a consumer restart. This synthetic development-key check does not qualify the designated production installation. See [the rehearsal runbook](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_REHEARSAL.md).

Read [Choosing the Prediction Engine](Choosing-the-Prediction-Engine) before operating V3.

## V2 production prediction contract

- one prior-only hierarchical core;
- stable competitor identity;
- one exclusive evidence cutoff per event;
- calibrated forecast interval and separate performance spread;
- deterministic joint mark optimizer;
- explicit engine/model/calibration versions, provenance, warnings, degraded state, and ignored factors;
- manual judge authority remains explicit;
- the former numeric LLM cascade, local XGBoost selection, QAA scaling, block-quality adjustment, and 97/3 weighting are retired in V2.

V3 instead combines independent formula, ML, and LLM-council forecasts. Same-round fields share a frozen epoch; settled completions can update a later round. Its mark-free pre-field forecasts and exact-field marks remain distinct.

Start with [Quick Start](Quick-Start), then read [Prediction Methods](Prediction-Methods), [Handicap System](Handicap-System-Explained), and [Architecture](Architecture).
