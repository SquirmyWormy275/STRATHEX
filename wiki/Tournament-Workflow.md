# Tournament Workflow

## Single event

1. Configure event, wood, stands, and competitors.
2. Persist one evidence cutoff.
3. Calculate one STRATHMARK v2 field.
4. Review interval, spread, versions, optimizer, warnings, and provenance.
5. Approve or explicitly adjust.
6. Generate heats.
7. Record results to the canonical workbook.
8. Select advancers.
9. Recalculate the smaller field with the original cutoff.
10. Complete final placements and payouts.

## Save and recovery

Tournament JSON is structurally validated, written to a temporary file, flushed, verified, and atomically replaced. A valid rolling backup can recover a damaged primary.

Excel and ResultStore are not one atomic transaction. Excel succeeds first; ResultStore is attempted afterward. A derived-store error cannot roll back Excel.

## Brackets

Bracket seeding uses one v2 field calculation. Non-power-of-two fields propagate byes. Bracket result entry advances winners through linked matches and supports replay from saved state.

## Same-day results

Completed heats remain visible and are persisted as results, but they are excluded from the event's prior-only prediction because they are on or after the fixed cutoff.
