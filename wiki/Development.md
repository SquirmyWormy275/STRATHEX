# Development

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

STRATHMARK is pinned to an exact Git commit. Do not change the pin without fixed-cutoff direct/HTTP parity and a migration decision.

## Test isolation

Every test must use a copied workbook and explicit disposable database:

```powershell
$env:STRATHMARK_TEST_DB = "1"
$env:STRATHMARK_DB_PATH = "$env:TEMP\strathex-tests.db"
python -m pytest -p no:cacheprovider --basetemp "$env:TEMP\strathex-pytest"
```

Never import the API against an implicit production database. Restricted nested worktrees may also require Ruff's `--no-cache`.

## Change rules

- Keep the STRATHMARK adapter as the only live numeric boundary.
- Persist one evidence cutoff per event.
- Preserve IDs and all v2 metadata.
- Do not reintroduce same-day evidence, silent transport fallback, or cross-store atomic claims.
- Add RED tests before calculation changes.
- Re-run tournament replay, bracket-bye, state recovery, package, and parity gates.
- Update maintained docs and all affected wiki pages in the same change.

## Publishing

The GitHub wiki is a separate Git repository. Merge source first, then copy, review, push, and re-fetch the published wiki. A code PR alone does not publish it.
