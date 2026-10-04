# Development

Read [ONBOARDING.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/ONBOARDING.md)
and `AGENTS.md` before changing code. Use Python 3.13 in an isolated environment.

## Install contributor tools

From the repository root, create and activate a virtual environment as shown in
[Quick start](Quick-Start), then install the test extras:

```bash
python -m pip install -e ".[dev,api-test]"
```

STRATHMARK V2 is pinned to reviewed commit
`a231ad65fe82317516cc82a282761d73adb0c0e3`. Changing that dependency requires
fixed-cutoff Python/HTTP parity checks and a migration decision.

## Isolate tests before imports

Use synthetic data or a copied workbook. Never run tests against the live workbook
or an implicit production database. Each run needs a fresh temporary directory and
all four database paths configured before collection.

Linux:

```bash
test_dir=$(mktemp -d)
export STRATHMARK_TEST_DB=1
export STRATHMARK_DB_PATH="$test_dir/v2.sqlite"
export STRATHMARK_V3_DB_PATH="$test_dir/v3.sqlite"
export STRATHEX_PREDICTION_AUTHORITY_DB="$test_dir/authority.sqlite"
export STRATHEX_V3_COMMAND_DB="$test_dir/commands.sqlite"
python -m pytest -p no:cacheprovider --basetemp "$test_dir/pytest"
```

Windows PowerShell:

```powershell
$testDir = Join-Path $env:TEMP ([guid]::NewGuid().ToString())
New-Item -ItemType Directory $testDir | Out-Null
$env:STRATHMARK_TEST_DB = "1"
$env:STRATHMARK_DB_PATH = Join-Path $testDir "v2.sqlite"
$env:STRATHMARK_V3_DB_PATH = Join-Path $testDir "v3.sqlite"
$env:STRATHEX_PREDICTION_AUTHORITY_DB = Join-Path $testDir "authority.sqlite"
$env:STRATHEX_V3_COMMAND_DB = Join-Path $testDir "commands.sqlite"
python -m pytest -p no:cacheprovider --basetemp (Join-Path $testDir "pytest")
```

Run formatting and link checks:

```bash
python -m ruff check --no-cache .
python -m ruff format --check --no-cache .
python scripts/check_docs.py
```

## Keep the calculation boundary intact

Use the STRATHMARK adapter for live numerics. Preserve stable IDs, versions,
warnings and evidence. V2 keeps its exclusive cutoff; V3 freezes a round's epoch.
Do not introduce fallback between engines or transports, same-day V2 evidence,
or claims that Excel and ResultStore are one transaction.

Write a failing regression test before changing calculations. Run the affected
replay, bracket, recovery, packaging and parity checks. Synthetic fixture rehearsals
do not establish Windows V7 production eligibility.

## Update and publish documentation

Edit `README.md` and affected pages in `wiki/` together. Merge the source change,
then publish from a clean checkout at the exact merged `main` commit:

```bash
python scripts/publish_wiki.py --mode publish
```

The publisher pushes the separate GitHub wiki and verifies every remote page.
A merged code PR alone does not update the wiki.
