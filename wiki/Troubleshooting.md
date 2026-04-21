# Troubleshooting

Common errors, common causes, common fixes.

---

## Install / Import

### `ModuleNotFoundError: No module named 'strathmark'`

STRATHMARK didn't install with STRATHEX. Causes:

1. Pip couldn't reach GitHub (offline, firewall, proxy)
2. You're on Python 3.12 or older (STRATHEX requires 3.13+)
3. You ran `pip install` outside a virtualenv and hit permission issues

Fix:
```bash
# Offline / firewall case
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK

# Python version
python --version   # Must be 3.13+

# Reinstall cleanly
pip install -e ".[dev]" --force-reinstall
```

### `ImportError: cannot import name 'HandicapCalculator' from 'strathmark'`

STRATHMARK is installed but at an old version. Upgrade:

```bash
pip install --upgrade strathmark
# or for editable:
cd ../STRATHMARK && git pull && pip install -e .
```

### Stale `__pycache__` after code changes

Symptoms: edits to `woodchopping/*.py` don't take effect; old behaviors persist.

```bash
find . -type d -name __pycache__ -exec rm -rf {} +
```

Windows equivalent:
```powershell
Get-ChildItem -Path . -Filter __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
```

This is listed in the global CLAUDE.md as a standing rule — run it as a first diagnostic for unexplained behavior.

---

## Data

### `ValueError: Species 'X' not found in wood sheet`

A result references a species that isn't in the `wood` catalog.

Fix: Add the species to the `wood` sheet (at minimum: `Species`, `Janka Hardness`, `Specific Gravity`). Restart STRATHEX.

### `KeyError: CompetitorID` when loading

The `Results` sheet has a `CompetitorID` that doesn't exist in the `Competitor` sheet. Typically a data-entry error (wrong ID) or a deleted competitor that still has historical records.

Fix: Re-add the competitor (use the same ID, or update `Results.CompetitorID` to point to an existing one).

### `BLOCKED: Insufficient [EVENT] history (N=2)`

The competitor has fewer than 3 results on this event. STRATHEX refuses to predict from N<3.

Fix: Add 1+ more historical results in the `Results` sheet, OR assign a panel mark (15 for open SB/UH) by hand and enter the tournament manually.

### `mixed-case event codes detected` warning at startup

Your Excel has a mix of `uh` and `UH` (or `sb` and `SB`) records. V5.1 fixed this — STRATHEX normalizes all event codes to uppercase at load. The warning is informational; no action needed.

### Handicap predictions look wildly off for one competitor

Most common causes:
1. **Outdated history.** Competitor hasn't raced in 5+ years; time-decay has pushed their weight to near-zero; prediction is coming from a sparse very-old baseline.
2. **Wrong species.** Check the wood selection against the `wood` sheet.
3. **Wrong quality.** Firmer than you entered? Try re-running with a different Q value.
4. **Bad outlier.** A record with `Time = 180.0` (DNF) made it past the 3×IQR filter because the surrounding variance is high. Edit or remove the outlier from the `Results` sheet.

Diagnostic path:
```python
# In a Python shell
from woodchopping.data.excel_io import load_all_data
competitors_df, wood_df, results_df = load_all_data('woodchopping.xlsx')

# Look at the problem competitor's history
print(results_df[results_df['Name'] == 'Problem Person'])
```

---

## Ollama / LLM

### `Connection refused: http://localhost:11434/api/generate`

Ollama isn't running. Start it:

```bash
ollama serve                      # Foreground
# or on Linux:
systemctl start ollama             # If installed as a service
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

### `Model 'qwen2.5:7b' not found`

Pull it:
```bash
ollama pull qwen2.5:7b
```

~4.5GB download. Or use a smaller model by editing `config.py` → `DEFAULT_MODEL`.

### LLM predictions are slow (10+ seconds per competitor)

Expected if Ollama is running on CPU rather than GPU. Workarounds:

1. Enable GPU acceleration in Ollama (check their docs for your platform)
2. Use a smaller model — `qwen2.5:1.5b` is 10x faster but less accurate
3. Disable LLM predictions entirely — ML + Baseline is often sufficient

To disable: set `ENABLE_LLM = False` in `config.py`.

### `LLM fairness narration timed out`

Ollama is running but overloaded or the model is too large for your hardware. STRATHEX falls back to a statistical fairness summary automatically. Consider:

- Switch to a smaller model
- Reduce simulation size (less context for the LLM to chew on)
- Disable LLM fairness assessment and use only the statistical output

---

## Monte Carlo

### Simulation reports Poor fairness (>10% spread)

Causes in rough order of likelihood:

1. **Sparse data for one competitor.** Check the predictions — any with LOW confidence or warnings?
2. **Wood quality mismatch.** The predictions assume one thing; the wood is another.
3. **Cross-diameter scaling error.** A competitor's history is all on 325mm blocks but today's wood is 250mm — QAA scaling is an approximation that can miss.
4. **Recent form change.** Competitor has been training hard / had an injury / changed equipment — historical data doesn't reflect reality.
5. **Bad manual override.** Did someone override a mark with incorrect intent?

Diagnostic path:
1. Re-examine the approval UI — look at confidence levels and warnings
2. Consider re-running with adjusted quality
3. Manually tweak the mark of the over/under-performing competitor and re-simulate

### Simulation takes forever / eats all my RAM

Iterations × competitors × per-simulation state = memory. Rough limits:

- 4 competitors @ 2M: ~64MB, ~3s
- 10 competitors @ 2M: ~160MB, ~5s
- 20 competitors @ 2M: ~320MB, ~10s
- 50 competitors @ 2M: ~800MB, ~30s (getting slow)

If you're running a huge exhibition with 50+ competitors, reduce iterations to 500K.

---

## Excel I/O

### `PermissionError: [Errno 13] Permission denied: woodchopping.xlsx`

Excel is open with the file — close it. STRATHEX needs exclusive write access.

On Windows, some cloud-sync tools (OneDrive, Dropbox) also lock files. Pause sync if this recurs.

### Results written but the Excel file looks unchanged

openpyxl atomic writes go to a tempfile then rename. If you have Excel open with the file during the write, the rename can fail silently. Check:

```bash
ls -la woodchopping.xlsx*   # Is there a .tmp sitting alongside?
```

If so, close Excel, delete the `.tmp`, re-run the save.

### New results don't appear in predictions next tournament

The SQLite ResultStore migration runs on startup. If you wrote results manually to Excel (bypassing STRATHEX), restart STRATHEX to trigger re-migration:

```bash
python MainProgramV5_2.py
```

You should see `[MIGRATION] Importing XX new results from woodchopping.xlsx...` in the startup log.

---

## Tournament state

### `tournament_state_<timestamp>.json` won't load

Caused by:
1. File corruption (rare — JSON is pretty robust)
2. State format change across versions (V5.2 → V6.0 has some breaking changes)
3. Referenced competitors or species have been deleted

Fix: Open the JSON in a text editor, check the error. If format-incompatible, you may need to re-enter the tournament from scratch. Going forward, V6.0+ state files should load reliably.

### Lost my tournament mid-event

Auto-save triggers after each round. Check for `tournament_state_*.json` files in the project root — the most recent one is your save. Load via Main Menu → Option 6.

---

## Testing / CI

### `pytest` fails on Windows but passes on Linux

Path separator issues. STRATHEX uses `pathlib` everywhere internally, but some older test fixtures may have hardcoded forward slashes. File an issue if you hit this.

### CI fails with `No module named 'ollama'`

Tests marked `@pytest.mark.ollama` need a local Ollama instance. CI skips them with `-m "not ollama"`. If you're seeing them run in CI, the marker isn't being applied — check the test file header.

---

## When all else fails

1. **Search the [STRATHEX issues](https://github.com/SquirmyWormy275/STRATHEX/issues)** and [STRATHMARK issues](https://github.com/SquirmyWormy275/STRATHMARK/issues).
2. **Clear the cache** (see "Stale `__pycache__`" above).
3. **Verify data integrity** — open `woodchopping.xlsx`, look at the row count, scan for obvious oddities.
4. **Reproduce minimally.** Can you trigger the bug with a 3-competitor test case? If so, include it in the issue.
5. **File an issue** with: Python version, STRATHEX commit hash, STRATHMARK version, full traceback, minimal repro.

---

## Further reading

- [Development](Development) — how to contribute fixes
- [Data Model](Data-Model) — schema details, validation rules
- [FAQ](FAQ) — general questions
