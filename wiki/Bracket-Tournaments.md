# Run a bracket

Use the single-event bracket workflow. STRATHMARK-backed seeding supports up to
**64 competitors**. Fields need not be a power of two; automatic byes fill the gaps.

## Seed the field

Seeding uses forecasts from the competition's selected engine. Seed 1 is the
fastest predicted competitor; later seeds follow increasing cutting time.

V3 seeding forecasts are signed and contain no handicap marks. The bracket retains
the requested and returned engine evidence. Regenerating a bracket keeps the same
competition authority; child rounds cannot choose another engine.

## Run matches

Single- and double-elimination structures connect winners and losers through match
IDs. Byes advance after links are established. Record a valid match result before
advancing its winner.

Save and reload preserve competitors, match status and links. Check those details
when resuming before entering the next result.

## Current limitation

Brackets inside a multi-event day are not supported. Use a single-event bracket
rather than adding a legacy bracket entry to a tournament save.
