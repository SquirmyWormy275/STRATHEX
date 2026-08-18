# Project Structure

## Entry point

- `MainProgramV5_2.py` — terminal menus, startup, single-event orchestration, and save/load.
- `explanation_system_functions.py` — concise operator help for the live v2 contract.

## Live package

```text
woodchopping/
  analytics/                 prediction accuracy and reporting
  data/
    excel_io.py              canonical workbook writes + best-effort ResultStore
    history_merge.py         de-duplicated Excel/store evidence
    store_registry.py        process-local ResultStore registry
  handicaps/
    calculator.py            live field preparation and v2 call
  simulation/                local Monte Carlo and fairness display
  ui/
    bracket_ui.py            brackets and v2 seeding
    championship_simulator.py v2 raw-time championship simulation
    multi_event_ui.py        multi-event workflow
    prediction_display.py    v2 evidence tables
    state_persistence.py     atomic JSON save and recovery
    tournament_ui.py         heat progression
  prediction_context.py      persisted exclusive evidence cutoff
  strathmark_adapter.py      Python/HTTP v2 boundary and persistence facades
```

## Compatibility code

`woodchopping/predictions/` contains archived local predictor and diagnostic modules used by historical audits. It is no longer imported eagerly, and live v7 calculation does not use its XGBoost, Ollama, expected-error, QAA, or 97/3 behavior.

Older solution reports remain compatibility/history surfaces. New calculation logic belongs at the STRATHMARK adapter boundary, not in archived predictor modules.

## Tests

Current release-critical tests cover:

- direct/HTTP fixed-cutoff parity;
- identity and metadata mapping;
- API version and transport security;
- prediction cutoff state;
- bracket v2 seeding and bye propagation;
- single/multi-event replay;
- atomic state persistence and recovery;
- canonical Excel write safety;
- clean-package imports.

Standalone scripts and archived validation programs are not automatically release-critical merely because their function names start with `test_`.

## Data

- `woodchopping_clean.xlsx` — tracked seed/reference workbook.
- configured live workbook — judge-canonical operational data.
- `saves/` — recoverable single/multi-event state.
- STRATHMARK ResultStore — derived local history, not the canonical judge record.
- STRATHMARK PredictionLedger — separate receipt/settlement facility, not used by the public v7 calculation route.

Tests must use copied workbooks and explicit disposable database paths.
