# STRATHMARK 2.0 compatibility evaluation

**Decision for STRATHEX v6.0.1: retain commit `47bb143`.**

STRATHMARK 2.0 retains many import names and compatible-looking signatures, but
it deliberately changes the calculation contract STRATHEX currently presents
to judges. An import smoke test is therefore insufficient evidence for a pin
change.

## Confirmed behavioral differences

- Same-tournament results supplied for later-round weighting no longer affect
  the 2.0 prediction.
- Wood quality remains accepted by the data shape but is numerically inactive.
- Supplied legacy ML and numeric LLM inputs are ignored by 2.0; an in-memory
  probe returned neither method as an available numeric prediction.
- Selection changes from expected-error scoring to a fixed authority order.
- Mark assignment uses the new joint optimizer instead of the pinned rounded-gap
  behavior. For fixed selected times `[62, 48, 31]`, the candidate produced
  marks `(3, 17, 33)` while the pinned contract produces `(3, 17, 34)`.
- Undated history is excluded by the new evidence-cutoff rules.
- STRATHEX does not yet supply stable competitor IDs, an explicit evidence
  cutoff, or surface the new warning/provenance/optimizer fields.

These are product decisions, not packaging defects. Adopting 2.0 would require
an explicit decision to retire or replace quality adjustment, same-wood
later-round weighting, numeric ML/LLM comparison, expected-error selection, and
rounded-gap marks.

## Upgrade gate

A future compatibility branch must compare pin and candidate in separate clean
environments using fixed-cutoff SB/UH fixtures; replay heat-to-final workflows;
golden-test method selection and mark rounding/optimization; migrate a copied
SQLite fixture; surface degradation and provenance evidence; prove one
prediction pass per competitor; and run with all network access disabled.

Until those gates pass and the behavior changes are accepted, `47bb143` is the
only supported STRATHEX engine revision.
