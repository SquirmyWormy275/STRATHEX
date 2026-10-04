# Simulation and fairness

STRATHEX can simulate a field after STRATHMARK returns predicted cutting times,
marks and performance standard deviations. Simulated races show how the field
might behave under those assumptions.

## Read the report

Reports can show win rates, podium chances, finish distributions and margins. Large
differences can help a judge decide which fields need closer review.

The simulation uses **performance spread** for race-to-race noise. A forecast
interval is uncertainty in the prediction and is not a substitute for that spread.

A simulation cannot prove equal real-world chances or rulebook compliance. Poor
predictions produce misleading simulations. Review warnings, degraded cases,
history quality and the complete field alongside the numerical report.

## Run limits

The championship simulator is capped at 250,000 races and a two-million
competitor-cell budget. Normal local CLI modes and STRATHMARK's REST `/simulate`
have separate limits. The REST endpoint is capped at 250,000 runs and its own
competitor-cell budget; it is not an interchangeable local mode.

## Official decisions

Judges determine legal outcomes and authorized adjustments. Historical narrative
LLM tools do not supply numeric authority. A close finish does not by itself prove
a valid handicap or cheating. See [Handicaps explained](Handicap-System-Explained)
and [Rules and officials](AAA-and-QAA-Rules-Compliance).
