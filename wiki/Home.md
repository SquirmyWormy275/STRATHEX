# STRATHEX 7.4.2

The separate [accuracy preview](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/tools/accuracy-preview/README.md)
compares frozen candidate and baseline cutting times on read-only snapshots. It carries
no competition authority and preserves STRATHEX's deliberate V2/V3 engine choice.

STRATHEX is the terminal application judges use to run woodchopping events. It handles rosters, wood setup, handicap and championship fields, brackets, multi-event days, schedules, results, autosave, and exports.

Numeric prediction and handicap marks come from the STRATHMARK engine deliberately selected for that competition. V2 remains the production baseline. V3 can use the complete separate Linux competition profile with actual Formula + trained ML, optimized exact fields, deliberate judge approval, separate issue, complete settlement, restart, official corrections and later-round learning. The LLM council is unavailable, and degraded or individual review is required. Retained numeric previews and Windows V7 rehearsal scopes keep their own contracts. See the [Linux competition runbook](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_LINUX_COMPETITION.md).

The retained Windows V7 rehearsal pins its service to security-maintained source `8a1d40aa5645715f9ab876d0517b64c36602a77e`. Linux and Windows CI exercise installed consumer/service wheels over loopback, including approval/issue separation and exact settlement recovery after a consumer restart. This synthetic development-key check does not qualify the designated production installation. See [the rehearsal runbook](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_REHEARSAL.md).

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

The full V7 design combines independent formula, ML, and LLM-council forecasts; the current Linux local profile uses verified Formula + ML with the council unavailable. Same-round fields share a frozen epoch; settled completions can update a later round. Its mark-free pre-field forecasts and exact-field marks remain distinct.

Start with [Quick Start](Quick-Start), then read [Prediction Methods](Prediction-Methods), [Handicap System](Handicap-System-Explained), and [Architecture](Architecture).

[Portable installation and rollback](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PORTABLE_INSTALLATION.md) retain exact older competition profiles. [Accuracy and local council diagnostics](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/ACCURACY_AND_COUNCIL.md) describe the improved Linux candidate and its development evaluation limits.
