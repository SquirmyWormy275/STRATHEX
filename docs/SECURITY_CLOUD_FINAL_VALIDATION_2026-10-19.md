# Security Cloud final-validation repairs — STRATHEX 7.4.6

The scan of `ee676a4ae6c4af75ea84e12d4aa4855f341b19b2` reported nine further
findings. The paths were checked independently and repaired as described below.
The earlier [7.4.5 repairs](SECURITY_CLOUD_FOLLOWUP_2026-10-19.md) remain in place.
This is a record of resolved reported paths, not a claim that a partial static scan
proves the absence of every possible vulnerability.

| Reported path | Resulting behavior and regression evidence |
| --- | --- |
| Remote V3 results written before issue authorization | Rehearsal is refused before any writer or result collection. Official local V3 requires an explicit-issue adapter and issued receipt rows, then settlement and checkpoint precede export. Single-event and multi-event regression paths cover issued and unissued rehearsal. |
| Workbook remapping changes the identity receiving a reviewed result | Compare reviewed stable IDs with the live roster before prompts and again in the exact workbook snapshot being saved. Late mismatches restore pending in-memory result fields and reach neither canonical sink. |
| Portable bundle and recovery helper lack an independent trust anchor | Require a manifest SHA256 from a separately protected reviewed record before parsing. The independently acquired bootstrap pins the paired helper SHA256 and executes the exact checked bytes. Self-consistent substituted artifacts and modified helpers are rejected. |
| Control characters enter official schedule text | Escape controls before line composition and bound displayed labels; retain original stored identities and make marks visible on their own competitor row. |
| Rehearsal marks exported as official schedules | Durable authority mode is checked at the shared official-use boundary and direct result-entry path. Rehearsal schedule attempts create no schedule file. |
| Workbook and save materialization is unbounded | Use the pinned producer's bounded workbook gateway before pandas/openpyxl; check regular-file identity and finite JSON-save bytes before allocating the entire input. Oversized dimensions and sparse saves stop before parsers. |
| Plaintext loopback workspace permits service impersonation | Require HTTPS for every browser workspace origin, including IPv4, IPv6 and localhost loopback. |
| Legacy workbook writer follows a replaceable path | Roster, historical time, legacy result and Linux result writes share private exclusive staging, synchronized descriptor writes, protected ancestry and unchanged-original checks. Symlink victims and concurrent replacement workbooks remain unchanged. |
| Selected runtime changes between readiness and execution | Check trusted ownership, ancestry, virtual environment configuration, importable files, hooks and base interpreter inputs before execution and recheck their captured identity on each later call. Preserve the original venv entry point; never change shared directory permissions. |

Regression coverage lives in `tests/test_final_security_boundaries.py`,
`tests/test_runtime_execution.py`, `tests/test_portable_installation.py`,
`tests/test_v3_issue_settlement_workflow.py`, `tests/test_workbook_recovery_guard.py`,
`tests/test_linux_results_security.py` and `tests/test_managed_launcher.py`.
The release also runs the complete isolated suite, Linux/Windows distribution
checks, documentation validation and a disposable installed-app competition smoke.

The runtime guard protects against a different local account or shared artifact
source replacing selected code. It is not a sandbox against the same operator
account or the administrator. Independently acquire the bootstrap and manifest
identity; a checksum shipped beside an untrusted bundle cannot authenticate it.
Existing saves, workbooks, model artifacts, keys, encrypted backups and historical
release assets are preserved. No production Windows signer or separate V3 witness
is fabricated by this release.
