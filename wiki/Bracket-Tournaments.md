# Bracket Tournaments

STRATHMARK-backed seeding supports at most 64 competitors. Automatic byes still handle non-power-of-two fields inside that limit.

Bracket seeding uses one STRATHMARK v2 field calculation. Seed 1 is the fastest predicted competitor; later seeds follow ascending predicted time.

The bracket stores v2 prediction metadata with each seed. The event's fixed evidence cutoff is reused when a bracket is regenerated.

Single- and double-elimination structures link winners and losers through explicit match IDs. Non-power-of-two fields create byes, and bye winners are propagated after links are established so the bracket cannot stall.

Result entry advances the winner only after a valid match is recorded. Save/reload validation checks match status, competitors, links, and bracket sections.

Multi-event bracket entries are currently rejected. Use the single-event bracket workflow until a dedicated combined contract is implemented and replay-tested.
