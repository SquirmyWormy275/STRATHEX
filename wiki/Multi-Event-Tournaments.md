# Run a multi-event day

Create the day through **Design a Tournament (Multiple Events)**. Set its date,
shared roster and prediction engine, then configure each event's competitors,
wood, format, rounds and payouts.

The tournament chooses V2 or V3 once. Child events and rounds inherit it; they do
not offer their own selector. Each event retains its evidence boundary for resume
and recalculation.

## Calculate and schedule

With V2, calculate each event's handicap field, review it and generate heats.
With Linux V3, obtain seeding times first, create exact heats and stands, then
calculate, approve and separately issue each field. Championship marks stay at 3.

Generate the day schedule after fields are ready. Check it against the event and
competitor assignments before export.

## Recalculate before results begin

Recalculation is blocked once results entry starts. Recalculating a scheduled event
invalidates its generated heats, so regenerate the day schedule afterward.

If recalculation fails, that event's old marks and pending rounds are cleared and
its status becomes `recalculation_failed`. Results and schedule export remain
blocked until calculation succeeds and the schedule is regenerated.

## Enter results and advance

Excel is the canonical result record. The separate ResultStore write retains the
tournament date and stable competition ID. JSON saves preserve the day and use
validation, atomic replacement and rolling backups.

V2 retains its original date cutoff and excludes same-day results. Linux V3 keeps
one round's evidence frozen, then learns from valid settled completions in later
rounds. Events advance independently; settle every field in an event's prior round
before advancing that event.

See [Tournament workflow](Tournament-Workflow) for results, issue and corrections.

## Brackets

Multi-event bracket entries are currently rejected. Run brackets through the
[single-event workflow](Bracket-Tournaments).
