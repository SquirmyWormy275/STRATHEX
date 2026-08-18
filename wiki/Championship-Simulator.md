# Championship Simulator

Championship mode predicts raw times with STRATHMARK 2 and assigns mark 3 to every competitor.

Each competitor prediction retains stable identity, cutoff, interval, performance spread, versions, provenance, warnings, and degraded state. Competitors sharing target wood and history context use one v2 field request. Competitor-specific wood or curated peak windows require separate requests because a STRATHMARK field calculation has one target wood profile and one evidence set.

The uncertainty report displays calibrated v2 intervals rather than disagreement among retired baseline/ML/LLM methods. Local Monte Carlo simulation estimates win and podium outcomes from predicted time and performance spread. It is capped at 250,000 races and adapts to field size under a two-million competitor-cell budget; unused raw finish-spread arrays are not retained.

Scenario comparisons reuse the original cutoff. They must not silently learn from same-day results.

The simulator is exploratory and view-only. Its output is not an official result, a formal fairness proof, or a production accuracy guarantee.
