# STRATHEX 7

STRATHEX is the terminal application judges use to run woodchopping events. It handles rosters, wood setup, handicap and championship fields, brackets, multi-event days, schedules, results, autosave, and exports.

Numeric prediction and handicap marks come from the STRATHMARK engine deliberately selected for that competition. V2 remains the production baseline. V3 is opt-in only when its exact authenticated readiness evidence permits it; rehearsal stays visibly labeled and is not a global cutover.

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
