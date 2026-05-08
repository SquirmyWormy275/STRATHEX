# Data and naming notice

This repository ships with a sample Excel data file (`woodchopping_clean.xlsx`) containing historical results for woodchopping competitors. The named individuals in that file, and in some wiki and documentation examples, are real competitors with public race results from AAA-sanctioned events.

The author has chosen to retain the real names rather than anonymize, on the basis that:

1. The race results themselves are public records, regularly published by event organizers and the AAA.
2. The data is used here only for prediction modeling and does not contain non-public personal information.
3. Anonymization would degrade the realism of the sample data and reduce the system's value as a portfolio piece.

Any named individual who would prefer their results not be included is welcome to open an issue or contact the author directly, and the data will be removed or replaced with a synthetic equivalent.

The system itself does not require real names to function. A synthetic roster of competitor IDs (e.g., `Athlete_01` through `Athlete_85`) can be substituted into the Excel file with no functional impact, since the prediction stack keys on `CompetitorID` rather than `Name`.
