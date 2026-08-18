# Version History

## 7.0.0

Breaking STRATHMARK 2 migration:

- direct v2 field calculation replaces the manual-override bridge;
- explicit Python and HTTP transports with fixed-cutoff parity;
- stable identity, calibrated intervals, provenance, warnings, and optimizer evidence;
- bracket and championship predictions routed through v2;
- same-day weighting, numeric LLM, local XGBoost selection, and QAA scaling retired;
- scikit-learn and XGBoost removed from runtime dependencies;
- pre-v2 ResultStore backup and stable competition IDs;
- maintained docs, in-app help, and wiki reconciled.

## 6.0.1

Maintenance release that repaired the STRATHMARK 0.4.1 bridge, prediction-display reuse, workbook recovery safety, tournament replay, atomic JSON state, bracket byes, packaging, and terminal rendering. Its dated release notes remain authoritative for that version.

## 5.x and earlier

Introduced multi-event operation, brackets, championship simulation, local predictor experiments, prompt tooling, and the early 97/3 tournament-weighting behavior. Those prediction semantics are historical and are not current in v7.
