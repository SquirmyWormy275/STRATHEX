# Monte Carlo Fairness

STRATHEX runs simulation locally after STRATHMARK returns predicted times, legal marks, and performance standard deviations.

The forecast interval is not used as race-to-race noise. Simulation uses performance spread. This distinction prevents model uncertainty from being mistaken for athlete variability.

Simulation output can include win rates, finish distributions, margins, and field summaries. It is decision support for a specific configured field, not a general accuracy or fairness guarantee.

Championship simulation uses an adaptive memory budget: no more than 250,000 races and two million competitor-cells. Aggregate results are retained; an unused list of every race's finish spread is not.

The normal CLI configuration, championship simulator, and STRATHMARK REST `/simulate` have different run limits. The public REST endpoint caps runs at 250,000 and also caps competitor-cells; it is not a transparent replacement for STRATHEX's larger local modes.

Narrative LLM output, if any remains in a historical compatibility tool, is not numeric prediction authority. Judges should rely on the numerical simulation, v2 provenance, warnings, and explicit manual review.
