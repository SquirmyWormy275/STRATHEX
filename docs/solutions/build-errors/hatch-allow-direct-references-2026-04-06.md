---
title: Hatchling rejects git+https direct references unless explicitly opted in
date: 2026-04-21
category: build-errors
module: packaging
problem_type: build_error
component: tooling
symptoms:
  - "`pip install -e .` fails in CI with hatchling refusing `git+https://...` URL"
  - "Direct-reference error surfaces on `pyproject.toml` dependency resolution"
  - "Error discovered only in CI; local editable installs tolerate the direct reference"
root_cause: config_error
resolution_type: config_change
severity: high
related_components:
  - development_workflow
tags: [hatchling, pyproject, strathmark, ci, git-dependency, direct-references]
---

# Hatchling rejects git+https direct references unless explicitly opted in

## Problem
STRATHEX's `pyproject.toml` lists `strathmark` as a `git+https://github.com/SquirmyWormy275/STRATHMARK.git@main` dependency so the sister engine is pulled automatically by `pip install -e .`. Hatchling (the build backend) refuses to accept direct references in `project.dependencies` by default, so CI failed on every install step even though local editable installs worked fine.

## Symptoms
- `.github/workflows/ci.yml` `pip install -e ".[dev]"` step exits non-zero across all matrix jobs (lint, test ubuntu, test windows, build wheel)
- `gh run view --log-failed` shows hatchling rejecting the `git+https://` URL in `project.dependencies`
- The failure does not reproduce locally at `pip install -e .` time because pip itself accepts PEP 440 direct references; hatchling's metadata validation is what rejects them, and that path only runs in a clean build

## What Didn't Work
- Assuming the dependency spec was wrong and rewriting the URL format. The URL itself is valid; hatchling's refusal is policy, not parsing
- Testing locally before pushing. Local `pip install -e .` succeeded, so the problem was invisible until CI ran

## Solution
Add the opt-in flag to `pyproject.toml`:

```toml
[tool.hatch.metadata]
# Required so the strathmark git+https direct reference in dependencies is allowed.
allow-direct-references = true
```

Four lines, dropped in above `[tool.hatch.build.targets.wheel]`. No other changes needed — the `strathmark @ git+https://...` line in `[project].dependencies` stays exactly as it was.

## Why This Works
PEP 440 direct references (`name @ url`) let packages depend on arbitrary URLs, including git repos. Hatchling treats this as an explicit opt-in because direct references break reproducibility in strict packaging contexts (they bypass PyPI, version pinning, and index policies). The `allow-direct-references = true` flag tells hatchling "we know what we're doing; this is intentional." Once set, the sister-repo dependency resolves normally and `pip install -e .` succeeds across platforms.

## Prevention
- When adding a `git+https://` dependency to a hatchling-backed project, set `[tool.hatch.metadata] allow-direct-references = true` in the same commit
- Run CI lint+install jobs on a PR branch before merging new dependencies, not after pushing to main. A clean build triggers hatchling's metadata validation; local editable installs do not
- If a sister repo becomes a long-term dependency, consider publishing it to PyPI later to avoid this flag entirely. The direct-reference approach is fine for now but worth revisiting if strathmark stabilizes

## Related Issues
- [README.md "CI/CD" section](../../../README.md) — documents the install flow this unblocks
- [CLAUDE.md "Dependency and Tooling Source of Truth"](../../../CLAUDE.md) — canonical rule that `pyproject.toml` is authoritative (no `requirements.txt`)
- [wiki/Ecosystem.md](../../../wiki/Ecosystem.md) — explains why strathmark is a git dependency rather than a PyPI release
- Commit e907e70 — the 4-line fix
