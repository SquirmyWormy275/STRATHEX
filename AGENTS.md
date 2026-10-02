# Contributor instructions

Before analyzing or changing predictions, marks, fields, simulations, or results, read the complete [STRATHMARK handicap foundations](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/wiki/Handicap-Mark-Math.md). Then read [ONBOARDING.md](ONBOARDING.md).

STRATHEX owns judge workflows, stable identities, persisted competition selection, official result entry, and Excel output. STRATHMARK owns numeric forecasts and marks. Keep one selected engine per competition root, no child overrides, and no fallback to another engine after failure. V2 is the production baseline. The separate Linux V3 competition profile supports the local lifecycle with explicit operator selection and persistent local keys; Windows V7 remains rehearsal-only and CNG qualification gates are unchanged.

Use synthetic workbooks and unique database and pytest temporary paths before collection. Never import MainProgramV5_2 during tests against operator paths: its legacy initialization opens data and begins the menu. Exercise menu functions without initialization or use the installed-app smoke with a disposable workbook.

Preserve existing competitor IDs, issued marks, official results, and independent backups. Pin changes, V3 source/contract identities, model artifacts, and signed evidence require coordinated review. Passing CI does not provision V3 production eligibility.

Update maintained docs and affected versioned wiki pages with behavior changes. Run focused regressions, the full isolated suite, Ruff, documentation links, distribution build, and installed-app smoke as appropriate. Publish the separate wiki only after merge, then verify remote page contents. Historical documents remain visibly dated.
