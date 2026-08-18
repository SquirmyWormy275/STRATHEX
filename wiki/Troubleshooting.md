# Troubleshooting

## HTTP mode says the URL is missing

Set both variables in the STRATHEX shell:

```powershell
$env:STRATHMARK_TRANSPORT = "http"
$env:STRATHMARK_API_URL = "http://127.0.0.1:8000"
```

## HTTP mode rejects a remote URL

Remote plaintext is intentionally blocked. Use HTTPS, or run the demo on `localhost` / `127.0.0.1`. Redirects and URLs containing credentials, paths, query strings, or fragments are also rejected; keep authentication outside the public stateless demo route.

## Version mismatch

STRATHEX 7 requires the audited STRATHMARK 2.0.0 `/calculate` schema and validates every result's audit metadata. Install the pinned commit from `pyproject.toml`; do not follow an unpinned branch.

## API unavailable

HTTP mode fails closed and will not switch to Python. Either restore the API or explicitly change `STRATHMARK_TRANSPORT=python` and recalculate as an operator decision.

## Degraded result or optimizer warning

Review each warning, engine/model/calibration version, cutoff, provenance, and optimizer field before approval. Do not hide degraded metadata.

## ResultStore migration

Before first v2 open, STRATHEX creates `results.db.pre-v2.bak`. Rehearse migration on a copy. Set `STRATHMARK_DB_PATH` explicitly so you know which store is in use.

## Workbook succeeds but ResultStore fails

The workbook is still canonical. The two writes are not atomic together. Preserve the warning, repair the derived store, then reconcile without duplicating Excel rows.

## Save file is malformed

The loader validates structure and can restore the valid `.bak`. If both are invalid, preserve both files and recover from the last known exported results rather than inventing state.

## Tests hang or cannot write cache in a restricted worktree

Use disposable paths and disable only tool caches:

```powershell
$env:STRATHMARK_TEST_DB = "1"
$env:STRATHMARK_DB_PATH = "$env:TEMP\strathex-tests.db"
python -m pytest -p no:cacheprovider --basetemp "$env:TEMP\strathex-pytest"
python -m ruff check --no-cache .
```

Never point tests at the live workbook or ResultStore.
