# Tournament Workflow

## Single event

1. Deliberately choose V2 or an eligible V3 mode for the event.
2. Configure event, wood, stands, and competitors.
3. Persist the competition authority and evidence boundary.
4. Calculate through the selected engine. V3 first produces a mark-free seeding forecast and later assembles marks from exact heats and stands.
5. Review requested/returned engine evidence, interval, spread, versions, optimizer or receipt, warnings, and provenance.
6. Approve or explicitly adjust.
7. Generate heats.
8. Record results to the canonical workbook.
9. Select advancers.
10. Recalculate the smaller field under the inherited engine authority.
11. Complete final placements and payouts.

## Save and recovery

Tournament JSON is structurally validated, written to a temporary file, flushed, verified, and atomically replaced. A valid rolling backup can recover a damaged primary.

Excel and ResultStore are not one atomic transaction. Excel succeeds first; ResultStore is attempted afterward. A derived-store error cannot roll back Excel.

## Brackets

Bracket seeding uses the selected engine's raw-time forecast. V3 uses a signed mark-free pre-field receipt. Non-power-of-two fields propagate byes. Bracket result entry advances winners through linked matches and supports replay from saved state.

## Same-day results

Completed heats remain visible and are persisted as results, but they are excluded from the event's prior-only prediction because they are on or after the fixed cutoff.
