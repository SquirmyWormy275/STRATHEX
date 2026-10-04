# Championship simulator

Choose **Championship Race Simulator (Fun Predictions)** from the main menu to
explore expected outcomes. This is a view-only tool, not an official result.

## What it shows

The selected engine predicts raw cutting times. Everyone starts at **Mark 3**;
a championship simulation does not turn the race into a handicap.

The report retains competitor identity, cutoff, uncertainty, performance spread,
versions and warnings. Local Monte Carlo simulation estimates win and podium
chances from those predictions and the assumed race-to-race spread.

It runs no more than 250,000 races and adapts to field size within a two-million
competitor-cell budget. Aggregate results are retained rather than unused arrays
for every race.

## Compare scenarios consistently

Keep the original cutoff and evidence when comparing scenarios. Do not mix model
bundles or compare one scenario after silently adding newer results.

Simulation is exploratory. It cannot prove real-world fairness, qualification or
future prediction accuracy. See [Simulation and fairness](Monte-Carlo-Fairness).
For an actual championship, use [Tournament workflow](Tournament-Workflow).
