# Troubleshooting

## The wrong workbook or roster opens

Restart with explicit `--workbook` and `--data-dir` paths, quoting spaces. Check any
explicit path environment settings; they can take precedence over launcher defaults.
Check the sheet names and headers in [Workbook and data](Data-Model).

Preserve your original workbook before repairing its schema. Do not create a new
empty workbook at the live path to get past a read error.

## V3 is unavailable or says preview/rehearsal

Read the label in [Engine selection](Choosing-the-Prediction-Engine). The full Linux
workflow requires `LINUX READY`, the separate Python 3.13 runtime, trained ML bundle,
persistent signing authority and independent recovery directory. Installing STRATHEX
alone does not supply these private artifacts.

`NUMERIC PREVIEW ONLY` cannot issue or settle. `REHEARSAL` does not grant Windows
production eligibility. Restore a saved competition's original profile; do not
switch it to V2 or a newer model to make the error disappear.

## V3 shows times but no marks

The pre-field forecast is for seeding. Generate actual heats and stand assignments,
then calculate and review complete-field marks. Approval and issue are separate:
confirm **Issue these approved marks now?** before official printing or results.

## A V3 command timed out

Its outcome may be uncertain. Reopen the same saved competition and use the displayed
durable command ID for exact retry/recovery. Keep the original source, model and
key. Do not create a replacement command or edit ledgers. See [Recovery](Backups-and-Recovery).

## A prediction is degraded or has optimizer warnings

Review the warning, cutoff, model, interval and field evidence before approving.
Linux V3's unavailable council requires deliberate degraded or individual review;
large Formula/ML disagreement requires individual review. Do not hide the warning
or treat a seeding forecast as an issued sheet.

## The workbook saved but ResultStore failed

The workbook is still the canonical result record. Preserve the warning and repair
the derived store, then reconcile without writing duplicate Excel rows. The two
writes are separate; a ResultStore failure does not undo Excel.

## A save file is malformed

From 7.4.5, the loader compares the complete save bytes to the private installation's
record. A changed, unbound, missing or historical save stops without activating its
`.bak`. Preserve both files and the authority database. Resume the original retained
profile where compatible, or independently review the complete recovery set. Do not
rewrite the JSON or clear the store to invent trust. See [Recovery](Backups-and-Recovery).

## V2 HTTP mode fails

Set both `STRATHMARK_TRANSPORT=http` and `STRATHMARK_API_URL` in the STRATHEX shell.
The API origin must have no credentials, path, query or fragment. Verified HTTPS is
required even on loopback. Provision a certificate for the configured hostname and,
for a private CA, set `STRATHMARK_API_CA_BUNDLE` to its trusted certificate file.
Redirects are rejected.

A schema mismatch or unavailable API stops calculation. Restore the configured
transport. A deliberate V2 transport change must preserve the reviewed contract
and evidence cutoff; it does not change the competition's selected engine.

For the local API setup, use
[STRATHMARK's API guide](https://github.com/SquirmyWormy275/STRATHMARK/wiki/REST-API).
The public V2 calculation route is stateless and has no client authentication; keep it on loopback behind the certificate-authenticated TLS endpoint.

## Migration or test failures

Before first V2 access, STRATHEX creates a `.pre-v2.bak` for an existing ResultStore.
Use an explicit `STRATHMARK_DB_PATH` and rehearse migration on a copy.

For test setup, use [Development](Development). Tests need fresh temporary database
paths set before imports and a copied or synthetic workbook.
