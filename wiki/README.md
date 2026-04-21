# STRATHEX Wiki Source

This directory is the source of truth for the [STRATHEX GitHub Wiki](https://github.com/SquirmyWormy275/STRATHEX/wiki).

## Files

| File | Purpose |
|---|---|
| `Home.md` | Wiki landing page |
| `_Sidebar.md` | Nav sidebar (shown on every page) |
| `_Footer.md` | Footer (shown on every page) |
| `Quick-Start.md`, `Architecture.md`, etc. | Content pages |

## One-time setup (first publish)

GitHub wikis require a first page created via the web UI before you can clone and push to them. Do this once:

1. Go to https://github.com/SquirmyWormy275/STRATHEX/wiki
2. Click **"Create the first page"**
3. Enter any title (e.g., `Home`) and any body (e.g., `seed`), click **Save page**
4. Then run the `publish.sh` script below

## Publishing updates

Run from the repo root:

```bash
bash wiki/publish.sh
```

This script:
1. Clones the wiki repo into a temp dir
2. Copies the latest `.md` files from `wiki/` over it
3. Commits and pushes

## Editing

- Edit pages here in `wiki/`, commit to the main STRATHEX repo.
- Run `bash wiki/publish.sh` to sync to the GitHub wiki.
- This way the wiki is version-controlled alongside the code — no drift, no dual maintenance.
