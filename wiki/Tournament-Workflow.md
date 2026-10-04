# Run a competition

## Set up the competition

For one event, use **Design an Event (Single Event)**. For a day of several events,
use **Design a Tournament (Multiple Events)**. Choose V2 or an available V3 runtime
at creation. A tournament's events and rounds keep that choice.

Set the date, event, wood, competitors, stands and format. Check stable competitor
IDs and the actual field before running a race.

## V2: calculate, review and run

1. Calculate predictions and marks through V2.
2. Review the times, intervals, warnings and handicap sheet.
3. Record any authorized manual mark adjustments explicitly.
4. Generate heats and check the start sheet.
5. Enter raw cutting times and official outcomes.
6. Select advancers and recalculate the complete next field.
7. Complete final placings and payouts, then save.

The event retains its original exclusive history cutoff. Same-day results are
saved, but are excluded from its V2 predictions. There is no 97/3 tournament blend.

## Linux V3: create fields, approve, issue and settle

This workflow requires the configured `LINUX READY` competition runtime. Older
numeric previews and rehearsal fixtures do not provide the same authority.

1. Obtain mark-free forecasts for seeding.
2. Generate the actual heats and stand assignments.
3. Calculate proposed marks for each exact field.
4. Open the review queue and deliberately approve each affected field. Linux's
   unavailable council requires degraded or individual review.
5. Confirm **Issue these approved marks now?** as a separate action.
6. Check the issued official sheet and run the race.
7. Enter an outcome for every issued competitor and authorize official placings.
8. Settle all fields in that event's round before advancing.
9. Generate the next round, review and issue its new fields, then continue to closure.

Declining issue leaves an approved but unissued field. Official printing and
results remain blocked until issue is acknowledged. Championship fields receive
signed fixed Mark 3 receipts.

## Enter V3 outcomes correctly

Use raw cutting seconds, or `DNF`, `DQ`, `DNS`, `VOID`. A penalty is entered as
`PENALTY <raw seconds> <penalty seconds>`. Record every competitor on the issued
sheet. Preserve the judge's official placings and ties.

Nonfinish and penalty rows do not become raw-time training evidence. All fields
in one round use frozen evidence. Valid settled completions can affect a later
round; separate events advance independently.

## Save, resume and correct

Save before closing. **Load Previous Event/Tournament** restores validated state;
JSON writes use atomic replacement and rolling backups. Excel is the canonical
result record. The separate best-effort ResultStore write does not make those
stores one transaction.

V3 commands and acknowledgments are durable. If a submission is interrupted,
resume with the same saved command and original runtime. Do not manufacture a
replacement command or key to get past a recovery block.

For official V3 corrections, use the same launcher with
`--correct-v3-results /absolute/path/to/saved-state.json`. Enter a reason and complete
revised outcomes. The signed revision preserves issued marks and previous evidence.
Review advancement separately after changing official results. Exact setup and
correction instructions are in the
[Linux competition runbook](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_LINUX_COMPETITION.md).

See [Backups and recovery](Backups-and-Recovery) before moving installations.
