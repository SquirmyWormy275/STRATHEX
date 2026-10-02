# STRATHEX 7.1.0

This release includes the competition-scoped engine selector and ASCII Wizard merged after 7.0.0, repairs outstanding July UI and identity defects, and supplies one portable Linux/Windows launcher.

V2 remains pinned to its reviewed 2.0.0 commit. V3 remains authenticated, source/contract-pinned, and rehearsal-only. Neither transport nor engine silently falls back. This release does not enable V3 production selection.

Before upgrading, preserve independent copies of the workbook, operator data directory, saves, ResultStore, prediction authority database, and V3 command database. Keep existing competitor IDs. Newly added competitors receive unique opaque IDs, including after roster rows have been removed.

Install the exact wheel into a Python 3.13 environment. Launch `strathex --workbook /absolute/path/to/workbook.xlsx --data-dir /absolute/path/to/operator-data`. Both Linux and Windows use this command; use platform-appropriate paths. The workbook is supplied separately and never shipped as operator data in the wheel.

Release gates are the complete isolated suite, Ruff, documentation links, exact distribution build, installed terminal startup/exit on Linux and Windows, hosted checks, and separately verified wiki publication. V3 installation/model/CNG qualification remains governed by STRATHMARK's deployment runbook.
