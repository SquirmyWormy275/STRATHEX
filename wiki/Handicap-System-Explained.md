# How handicap marks work

A smaller mark starts earlier. A faster expected competitor gets a larger mark
and waits longer, allowing the field to finish closer together.

## Two clocks

**Raw cutting time** starts when a competitor begins cutting. The **starter's count**
starts before the front marker begins. A finish measured from the starter's first
count includes the competitor's waiting time.

For a simple illustration:

| Competitor | Expected cutting time | Start mark | Expected finish count |
| --- | --- | --- | --- |
| A | 60 seconds | 3 | 63 |
| B | 45 seconds | 18 | 63 |
| C | 30 seconds | 33 | 63 |

The software also accounts for uncertainty and legal mark limits, so actual issued
marks need not equal independently rounded time gaps.

## Marks belong to a field

Marks are calculated together for the actual competitors in a heat or final.
Adding the same constant to every mark preserves relative waiting times. Changing
the competitors changes the field and requires recalculation and rebasing.

Do not copy one heat's displayed mark straight into a different final.
The shared [handicap reference](https://github.com/SquirmyWormy275/STRATHMARK/wiki/Handicap-Mark-Math)
has more worked examples, book-mark conversion and the role of officials.

## V2 and V3 evidence differ

V2 uses valid dated history strictly before the saved cutoff. If no date was entered,
the first calculation persists the operator computer's local calendar date. Same-day
heat times are recorded but do not alter its later-round predictions.

Linux V3 freezes evidence across the round. Once all fields are settled, valid
completed results can affect a later round. Its pre-field forecasts have no marks;
exact heats and stands come before calculation, approval and separate issue.

V2 wood quality and tournament weighting are inactive compatibility inputs. Neither
engine revives the old STRATHEX-side XGBoost/LLM selection or 97/3 blend.

## Review uncertainty and outcomes

The forecast interval and race-to-race performance spread describe different things.
Review warnings and the complete mark sheet. V2 manual adjustments are explicit
operator decisions. V3 requires its own approval and issue workflow.

Championship races use fixed Mark 3. Judges determine official placings, penalties
and legal outcomes under the event's governing rules.
