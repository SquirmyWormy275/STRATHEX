# Bracket Tournaments

STRATHMARK-backed seeding supports at most 64 competitors. Automatic byes still handle non-power-of-two fields inside that limit.

Bracket seeding uses forecasts from the engine selected for the competition. V2 preserves its existing calculation. V3 uses a signed pre-field forecast that cannot contain a handicap mark. Seed 1 is the fastest predicted competitor; later seeds follow ascending predicted time.

The bracket stores requested and returned engine evidence with each seed. The owning competition authority is reused when a bracket is regenerated; a child round cannot select another engine.

Single- and double-elimination structures link winners and losers through explicit match IDs. Non-power-of-two fields create byes, and bye winners are propagated after links are established so the bracket cannot stall.

Result entry advances the winner only after a valid match is recorded. Save/reload validation checks match status, competitors, links, and bracket sections.

Multi-event bracket entries are currently rejected. Use the single-event bracket workflow until a dedicated combined contract is implemented and replay-tested.
