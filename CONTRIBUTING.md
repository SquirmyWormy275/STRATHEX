# Contributing to STRATHEX

Start with [AGENTS.md](AGENTS.md) and [ONBOARDING.md](ONBOARDING.md). Use Python 3.13 on Linux or Windows and install `.[dev,api-test]` in a virtual environment.

Prove a defect with its actual trigger before repairing behavior. Keep synthetic workbooks and all database, authority, command, and pytest paths separate from operator data. Preserve stable identities and competition-root engine selection through save, resume, failure, and round progression. Numeric V2 behavior and V3 service contracts remain STRATHMARK responsibilities.

PRs must pass the named CI checks before merge. Ruff 0.16.5 and GitHub Actions are pinned; Dependabot proposes reviewed updates monthly. The STRATHMARK Git pin is deliberately excluded from automatic dependency updates. Coordinated pin changes need direct/HTTP parity, consumer tests, and a migration decision.

Record operator-visible changes in [CHANGELOG.md](CHANGELOG.md), maintained docs, and wiki source. Build and smoke the exact wheel on Linux and Windows before a release. The workbook is supplied separately; the wheel never includes operator data. Retain the original release tags and dated evidence.

Preview wiki changes with `python scripts/publish_wiki.py --mode preview`. From a clean merged source, publish with `--mode publish`, then independently compare using `--mode check`. The default preview performs no push.
