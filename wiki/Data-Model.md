# Workbook and saved data

## Workbook sheets

Start from a workbook with the supplied schema. Sheet lookup is case-insensitive.
Keep the headers below when editing in Excel; do not replace competitor IDs with names.

| Sheet | Headers |
| --- | --- |
| `Competitor` | `CompetitorID`, `Name`, `Country`, `State/Province`, `Gender` |
| `wood` | `Scientific Name`, `species`, `speciesID`, `country`, `region`, `janka_hard`, `spec_gravity`, `crush_strength`, `shear`, `MOR`, `MOE` |
| `Results` | `CompetitorID`, `Event`, `Time (seconds)`, `Size (mm)`, `Species Code`, `Quality`, `HeatID`, `Date` |

The application can add result metadata beyond these base headers. Preserve those
columns, including competition identity and outcome/correction information.

## Competitor identity

`CompetitorID` links a roster entry to historical results. Existing IDs are preserved;
new IDs are opaque UUID-backed identities. Deleting a competitor must not recycle
their ID for someone else. Names may change or be duplicated.

Names are local and judge-facing. V3 receives namespaced pseudonymous IDs and the
sporting facts needed to calculate, rather than using names as identity.

## Historical results

Use `SB` for standing block and `UH` for underhand. Store **raw cutting seconds**,
diameter in millimetres, the species code, quality, heat identity and a valid date.
The starter's elapsed count is not raw cutting time. Enter competition outcomes
through the application so their metadata remains consistent.

V2 uses valid dated history strictly before the saved prediction cutoff. Undated,
same-day, future and invalid rows do not contribute. Linux V3 freezes evidence for
a round and can admit valid settled completions at a later-round boundary.

## Where records live

| Record | Purpose |
| --- | --- |
| Excel workbook | Canonical competition results and roster/wood data. |
| JSON save | Event or tournament setup, fields, progress, results and payouts. |
| STRATHMARK ResultStore | Best-effort local historical evidence. |
| Engine-selection database | The competition's chosen engine and original authority. |
| V3 command ledger and receipts | Durable submissions, acknowledgments, forecasts, approvals, issued fields and settlements. |
| V3 runtime database, head and key | Signed local competition history and recovery authority. |

Excel is written first; ResultStore is a separate write. A successful workbook write
is not rolled back if ResultStore fails. JSON saves use validation, atomic replacement
and rolling backups.

The public V2 `/calculate` route reads its request and is stateless. Its separate
PredictionLedger is not automatically populated by STRATHEX's ordinary calculation.

Keep these records together when backing up. See [Backups and recovery](Backups-and-Recovery).
