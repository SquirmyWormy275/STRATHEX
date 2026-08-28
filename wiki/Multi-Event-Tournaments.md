# Multi-Event Tournaments

A multi-event day stores tournament metadata, one deliberate root engine selection, a shared roster, event-specific competitors, wood, format, rounds, marks, schedules, results, and payouts. Child events and rounds inherit the root selection and never expose their own selector.

The tournament date becomes the default exclusive STRATHMARK evidence cutoff. Each event persists its own copy so save/reload and recalculation remain reproducible.

With V2 selected, batch handicap calculation preserves the established V2 field contract. With V3 selected, mark-free forecasts support initial seeding; exact field membership and stand assignments are then sent for complete field-relative marks. Championship events keep mark 3. Later rounds inherit the tournament engine and recalculate their advancing field under its evidence contract; they never switch engines or apply an undocumented fallback.

Recalculation is blocked once results entry begins. Recalculating a scheduled event invalidates its generated heats. If recalculation fails, the affected event's previous marks and pending rounds are cleared and its status becomes `recalculation_failed`. Results entry and schedule export stay blocked until that event calculates successfully and the day schedule is regenerated.

Results are written to Excel first. The best-effort ResultStore write includes the tournament date and a stable competition ID. Multi-event JSON saves use the same validation, atomic replacement, and backup recovery as single-event state.

Legacy bracket entries inside a multi-event day are rejected. Run a bracket through the single-event bracket workflow until a dedicated multi-event bracket contract is implemented and replay-tested.
