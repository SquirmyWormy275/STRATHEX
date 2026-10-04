# Maintain the STRATHEX wiki

This directory contains the source for the
[GitHub wiki](https://github.com/SquirmyWormy275/STRATHEX/wiki). `Home.md` is its
front page; `_Sidebar.md` and `_Footer.md` provide navigation. This README is not
published as a wiki page.

Write for the person doing the task. Put the action first, explain necessary
choices, and link to detailed specifications rather than repeating them. Keep
current behavior separate from dated release records. Engine labels and V2/V3
evidence rules must match the application.

Use extensionless links for other wiki pages and full GitHub links for repository
files. Add new pages to the sidebar and the relevant task guide.

Before merging:

```bash
python scripts/check_docs.py
```

After merging, from a clean checkout at the exact remote `main` commit:

```bash
python scripts/publish_wiki.py --mode publish
```

The script copies the pages, pushes the separate wiki and verifies their remote
contents. `--mode preview` shows the changes; `--mode check` checks the published
wiki against the current source.
