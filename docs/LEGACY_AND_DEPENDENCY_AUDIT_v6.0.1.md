# Legacy and dependency audit — v6.0.1

> Historical v6.0.1 audit. STRATHEX 7 removes the live XGBoost/scikit-learn dependency and uses STRATHMARK 2 for all prediction surfaces.

This audit traces imports from `MainProgramV5_2.py`, the declared
`woodchopping.predictions` public surface, tests, validation scripts, and CLI
entry points. It separates code that is merely old from code that is provably
unreachable inside this repository.

## Removed orphan cluster

Seven prediction modules had no path from the application, no public export,
no test or script caller, and no command-line entry point:

- `calibration.py`
- `diameter_diagnostic.py`
- `lightgbm_model.py`
- `production.py`
- `randomforest_model.py`
- `ridge_model.py`
- `stacking_ensemble.py`

The only links in that cluster were `production -> stacking_ensemble` and the
stacking module's imports of LightGBM, random-forest, and ridge helpers. The
archived redesign report is the only retained reference and is now explicitly
marked historical.

`lightgbm` was imported only by that orphan cluster. `matplotlib` had no Python
import anywhere in the repository. Both were therefore removed from runtime
dependencies.

## Retained compatibility paths

The older baseline, XGBoost, LLM, prediction-aggregator, and check-my-work
modules remain live. They are still called by the main comparison screen,
bracket seeding, the championship simulator, multi-event analysis displays,
or standalone validation scripts. Removing them in a patch release would
silently remove judge-facing behavior.

The remaining prediction stack should be migrated behind explicit STRATHMARK
adapter contracts in a separate, behavior-preserving change before any further
deletion.

## Verification gates

The v6.0.1 release requires:

1. assertion-based imports of the declared prediction public API;
2. the complete isolated pytest suite and Ruff checks;
3. a wheel built from a clean tree;
4. imports of public STRATHEX packages from outside the repository checkout.

The repository cannot prove that an undocumented external program never
imported one of the removed private modules. The `v5.2-legacy` branch and this
release audit provide the compatibility record.
