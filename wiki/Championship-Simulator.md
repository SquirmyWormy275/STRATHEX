# Championship Simulator

Championship mode predicts raw times with the competition's selected STRATHMARK engine and assigns mark 3 to every competitor.

Each competitor prediction retains stable identity, cutoff, interval, performance spread, versions, provenance, warnings, and degraded state. V2 preserves its established field calculation. V3 may supply its supported mark-free forecast evidence, but it never converts a scratch championship into a handicap event.

The uncertainty report displays the selected engine's supported uncertainty evidence rather than disagreement among retired STRATHEX-side baseline/ML/LLM methods. Local Monte Carlo simulation estimates win and podium outcomes from predicted time and performance spread. It is capped at 250,000 races and adapts to field size under a two-million competitor-cell budget; unused raw finish-spread arrays are not retained.

Scenario comparisons reuse the original cutoff. They must not silently learn from same-day results.

The simulator is exploratory and view-only. Its output is not an official result, a formal fairness proof, or a production accuracy guarantee.
