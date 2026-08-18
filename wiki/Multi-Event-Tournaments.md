# Multi-Event Tournaments

A multi-event day stores tournament metadata, a shared roster, event-specific competitors, wood, format, rounds, marks, schedules, results, and payouts.

The tournament date becomes the default exclusive STRATHMARK evidence cutoff. Each event persists its own copy so save/reload and recalculation remain reproducible.

Batch handicap calculation calls STRATHMARK v2 once per handicap field. Championship events keep mark 3. Later rounds recalculate their advancing field under the original cutoff; they do not apply 97/3 same-day weighting.

Recalculation is blocked once results entry begins. Recalculating a scheduled event invalidates its generated heats. If recalculation fails, the affected event's previous marks and pending rounds are cleared and its status becomes `recalculation_failed`. Results entry and schedule export stay blocked until that event calculates successfully and the day schedule is regenerated.

Results are written to Excel first. The best-effort ResultStore write includes the tournament date and a stable competition ID. Multi-event JSON saves use the same validation, atomic replacement, and backup recovery as single-event state.

Legacy bracket entries inside a multi-event day are rejected. Run a bracket through the single-event bracket workflow until a dedicated multi-event bracket contract is implemented and replay-tested.
