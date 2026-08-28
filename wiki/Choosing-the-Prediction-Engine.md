# Choosing the Prediction Engine

## Where the choice is made

- Single event: choose once during event setup.
- Multi-event tournament: choose once at tournament creation.
- Tournament child events, heats, semifinals, and finals inherit the root choice. They never show their own selector.

Nothing is selected by default. The judge records a reason, and the choice locks when the first authoritative prediction or calculation begins.

## V2

V2 is the established deterministic production baseline. It keeps the existing prior-only prediction, fixed evidence cutoff, and joint mark optimizer unchanged.

## V3

V3 can be selected only when its authenticated local service returns the exact reviewed contract and source identity. `REHEARSAL` means non-production and remains visible throughout the competition.

V3 has two deliberately different outputs:

1. A pre-field forecast estimates raw completion time for seeding. It contains no mark and cannot be approved or issued as a mark sheet.
2. After exact heat membership and stand positions exist, V3 prepares every competitor card and assembles the complete field-relative marks.

Ordinary green/amber fields can be mass approved. Degraded fields require a separate deliberate batch. Flagged fields are opened individually for accept, exclude, or defer.

## Failure and recovery

There is no fallback between engines. If V3 is unavailable, incompatible, incomplete, or ambiguous, new numeric work stops. For an ambiguous command, STRATHEX displays its durable identity and the judge may retry that exact command or leave the scope blocked. Existing issued marks and results are never re-ranked.

V3 service credentials are installation controls, not competition choices. STRATHEX
stores only an environment-variable or OS-keyring reference and rereads it for every
request. Rotation and revocation are performed by the deployment administrator; the
judge workflow never displays or saves the one-time replacement secret.

## Championship events

Championship and bracket scratch rules remain Mark 3. The selected engine may supply supported predictions or seeding, but it does not turn a scratch event into a handicap race.
