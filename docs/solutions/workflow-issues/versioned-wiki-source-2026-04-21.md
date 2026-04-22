---
title: Keep GitHub wiki version-controlled by editing wiki/ in main repo and pushing via publish.sh
date: 2026-04-21
category: workflow-issues
module: documentation
problem_type: workflow_issue
component: documentation
severity: medium
applies_when:
  - Maintaining a GitHub wiki that must not drift from code it documents
  - Wiki pages are judge-facing or user-facing (trust depends on correctness)
  - Multiple contributors edit documentation and need code-review on wiki changes
related_components:
  - development_workflow
  - tooling
tags: [wiki, github-wiki, documentation, publish-script, versioned-docs, workflow]
---

# Keep GitHub wiki version-controlled by editing wiki/ in main repo and pushing via publish.sh

## Context
GitHub wikis are separate git repos (`<repo>.wiki.git`) with no branch protection, no PRs, and no link to the main repo's history. Anyone with wiki access can edit pages directly through the web UI, and those edits never show up in the main repo's `git log`. For STRATHEX this was a liability: the wiki is judge-facing (woodchopping competition organizers rely on it to understand how handicaps are calculated), so drift between the wiki and the codebase would destroy trust. The existing workflow had no versioning, no review, and no automated sync.

The fix was to treat the main repo's `wiki/` directory as the source of truth and publish from there with a small script. Edits go through normal commits and PRs; publishing is a single command.

## Guidance
**Store wiki pages in the main repo under `wiki/`, and sync to the GitHub wiki git remote via a publish script.** This gives the wiki the same review and versioning properties as code.

Repository layout:

```
wiki/
├── README.md             # Explains the workflow (not published to wiki)
├── publish.sh            # Sync script (not published to wiki)
├── Home.md               # Wiki landing page
├── _Sidebar.md           # Nav sidebar (GitHub wiki convention)
├── _Footer.md            # Footer (GitHub wiki convention)
├── Quick-Start.md        # Content page
├── Architecture.md       # Content page
└── ...                   # 17 content pages total
```

The publish script clones the wiki remote, copies the tracked `wiki/*.md` files over, commits, and pushes. Pages named `README.md` are stripped before publish so the operator doc stays private to the main repo:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO="SquirmyWormy275/STRATHEX"
WIKI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

git clone "https://github.com/${REPO}.wiki.git" "$TMP_DIR"
cp "${WIKI_DIR}"/*.md "$TMP_DIR/"
rm -f "$TMP_DIR/README.md"

cd "$TMP_DIR"
git add -A
if git diff --cached --quiet; then
    echo "No changes to publish."
    exit 0
fi
git commit -m "Update wiki from STRATHEX/wiki/"
git push origin HEAD
```

**One-time GitHub UI seed:** before the wiki git remote is accessible, the wiki must be initialized via the web UI. Direct `git push` to an empty `<repo>.wiki.git` fails at the remote end, not locally — GitHub refuses to create the wiki backend without a web-UI "Create the first page" click. The `wiki/README.md` in this repo documents that step so a new operator knows the first run requires clicking through the browser.

## Why This Matters
Without a sync workflow:

- The main repo and the wiki drift. Code changes never propagate to wiki explanations, and wiki edits never land in the main repo. Judges eventually notice discrepancies and lose confidence.
- Wiki edits have no review. Anyone with wiki access can post inaccurate claims about how the system works, and there's no audit trail tying them to code.
- The wiki cannot be regenerated. If the wiki repo gets corrupted or a contributor accidentally deletes pages via the UI, history is harder to reconstruct than a normal git repo — there's no PR stream to grep.

With this workflow:

- Wiki edits flow through normal commits on `main` (or a branch + PR) and get the same review, ruff/CI enforcement, and blame as code.
- The main repo's `git log` is the canonical history of wiki changes. The wiki git repo is just a publish target.
- `bash wiki/publish.sh` is idempotent: if the working copy matches the wiki, it says "No changes to publish." and exits. Safe to run from automation or by hand.
- New operators only need to know two commands: edit `wiki/*.md`, then `bash wiki/publish.sh`.

## When to Apply
- Any project with a GitHub wiki that documents code behavior, API contracts, or user-facing procedures that must stay in sync with the codebase
- Projects with multiple contributors where wiki accuracy matters (judge-facing, customer-facing, compliance-relevant)
- Projects where the wiki is large enough that manual sync via the web UI would guarantee drift (STRATHEX has 17 content pages — anything in that range or larger)

## Examples

**Before** — no versioning, direct edits in GitHub UI:

```
Author edits Architecture page via github.com/.../wiki/Architecture
-> Change lives only in the wiki git repo
-> Main repo's Architecture.md (if it exists) is now stale
-> No PR, no review, no grep-ability
```

**After** — versioned in `wiki/`, published via script:

```
$ vim wiki/Architecture.md
$ git commit -am "wiki: update Architecture section for V6.1"
$ git push origin main
$ bash wiki/publish.sh
Cloning wiki repo...
Copying markdown pages...
[main 3f4d2a1] Update wiki from STRATHEX/wiki/
 1 file changed, 12 insertions(+), 3 deletions(-)
Wiki published: https://github.com/SquirmyWormy275/STRATHEX/wiki
```

## Related
- [wiki/README.md](../../../wiki/README.md) — primary operator guide for editing and publishing
- [wiki/publish.sh](../../../wiki/publish.sh) — the sync script itself
- [CLAUDE.md "DOCUMENTATION SYNC"](../../../CLAUDE.md) — standing order that `wiki/` is now part of the sync obligation
- [docs/INDEX.md](../INDEX.md) — top-level doc index; should gain a pointer to the versioned wiki
- Commit c891c65 and PR #1 — where the wiki source and publish script landed
