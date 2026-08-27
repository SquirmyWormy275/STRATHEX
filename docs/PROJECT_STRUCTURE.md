# Project Structure

## Entry point

- `MainProgramV5_2.py` — terminal menus, startup, single-event orchestration, and save/load.
- `explanation_system_functions.py` — concise operator help for engine selection and live contracts.

## Live package

```text
woodchopping/
  analytics/                 prediction accuracy and reporting
  data/
    excel_io.py              canonical workbook writes + best-effort ResultStore
    history_merge.py         de-duplicated Excel/store evidence
    store_registry.py        process-local ResultStore registry
  handicaps/
    calculator.py            live field preparation and routed calculation
  simulation/                local Monte Carlo and fairness display
  ui/
    bracket_ui.py            brackets and selected-engine seeding
    championship_simulator.py selected-engine forecasts with fixed Mark 3
    multi_event_ui.py        multi-event workflow
    prediction_display.py    requested and returned engine evidence
    prediction_context.py    canonical SQLite engine authority
    state_persistence.py     atomic JSON save and recovery
    tournament_ui.py         heat progression
  engine_selection.py        immutable no-fallback engine router
  prediction_context.py      persisted exclusive evidence cutoff
  strathmark_adapter.py      Python/HTTP v2 boundary and persistence facades
  strathmark_v3_client.py    authenticated V3 lifecycle and receipt validation
  v3_authority_store.py      durable V3 command/recovery ledger
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
- no-default selection, root inheritance, locking, and migration;
- V3 pre-field forecasts, exact-field marks, review, and recovery;
- requested/returned engine identity and no-fallback routing;
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
- STRATHMARK V2 PredictionLedger — separate from the public V2 calculation route.
- STRATHMARK V3 receipts — used only by a V3-selected scope through the authenticated lifecycle.

Tests must use copied workbooks and explicit disposable database paths.
