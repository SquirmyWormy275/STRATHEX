# Architecture

STRATHEX owns the judge's workflow. STRATHMARK owns numeric predictions, mark
optimization and engine eligibility. Every calculation uses the engine deliberately
chosen for the competition; it cannot silently switch.

## Application flow

```text
Judge -> STRATHEX menus -> selected STRATHMARK engine
             |                   |
             |              times, marks, evidence
             |
             +-- workbook results
             +-- JSON saves and engine-selection records
             +-- local history and V3 command/receipt records
```

## Calculation connections

| Connection | Use |
| --- | --- |
| V2 direct Python | Default local calculation; offline-capable. |
| V2 HTTP | Explicit stateless calculation demo with complete field/history in the request. |
| Linux V3 subprocess | Separate Python 3.13 competition runtime with signed local authority. |
| V3 V7 service | Separate authenticated lifecycle pinned to an exact contract/source; Windows qualification remains incomplete. |

V3 pre-field forecasts supply seed times without marks. Exact heat membership and
stands are required before marks. Review and issue are separate steps.

## Records and boundaries

The workbook is canonical for results. JSON preserves competition progress.
ResultStore is a separate best-effort history write. V3 also retains durable command
IDs and signed lifecycle receipts. These stores are not one distributed transaction.

V2 calculation is distinct from its optional trusted PredictionLedger. Ordinary
STRATHEX V2 calculation does not write trusted ledger receipts.

## Championship scenarios

Competitors can be grouped when target wood and history context match. Different
wood or curated peak windows need separate calls. The simulator fixes its evidence,
rejects mixed model bundles and stops rather than returning a partial field.

For the module map and detailed interfaces, see the
[architecture document](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/ARCHITECTURE.md).
