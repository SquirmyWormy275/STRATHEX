# Development

For contributors, forkers, and anyone running the test suite.

---

## Local setup

```bash
git clone https://github.com/SquirmyWormy275/STRATHEX.git
cd STRATHEX
pip install -e ".[dev]"           # Core + ML + dev tools
pip install -e ".[dev,llm]"       # Add optional LLM client
```

For engine development, also clone STRATHMARK as a sibling:

```bash
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK
```

See [Quick Start § Editable STRATHMARK](Quick-Start#editable-strathmark-for-engine-developers).

---

## The local loop

```bash
# Edit code
vim woodchopping/some_file.py

# Run tests (skipping Ollama-dependent tests — same as CI)
pytest tests/ -v -m "not ollama"

# Run all tests (if you have Ollama available)
pytest tests/ -v

# Coverage report
pytest tests/ --cov=woodchopping --cov-report=term-missing

# Lint
ruff check .
ruff format --check .       # Or `ruff format .` to apply

# Verify the wheel builds and imports
python -m build
python -c "import strathmark; print(strathmark.__version__)"
```

All four checks (lint, test, build, import) run in CI on every push. Match them locally before pushing.

---

## Project conventions

### Style

- Ruff for lint + format. Config in [`pyproject.toml`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/pyproject.toml).
- Snake_case functions. Type hints where practical (not enforced on legacy code).
- No emojis in source code or user-visible CLI output. Plain ASCII only.
- Box-drawing characters (╔╗╚╝║═) for CLI banners — see the ASCII Art Alignment standing rule in [`CLAUDE.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/CLAUDE.md).
- 70-character banner width. Use Python's `.center(68)` for alignment.

### Architecture

- STRATHEX never touches the math directly. Everything goes through `woodchopping/strathmark_adapter.py`.
- DataFrame ↔ typed-object conversions live only in the adapter.
- New tournament formats are added as files under `woodchopping/ui/` with their own state dict.
- Excel I/O uses openpyxl (not pandas `to_excel`) for atomic appends.

### Tests

- Tests that need Ollama must be marked `@pytest.mark.ollama`. CI skips these.
- Tests that write to files must use pytest's `tmp_path` fixture. **Never write to the real `woodchopping.xlsx` or the real `~/.strathmark/`.**
- Integration tests go in `tests/integration/`. Unit tests are alongside the code they test.
- Validation suites (backtesting, model comparison) live in `tests/validation/`.

### Documentation

- Every code change that affects functionality must update the relevant docs (standing rule from CLAUDE.md).
- Prediction-engine changes specifically must update [`explanation_system_functions.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/explanation_system_functions.py) — that's the in-app educational wizard judges read.
- Prompt changes must be logged in [`docs/PROMPT_CHANGELOG.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PROMPT_CHANGELOG.md).

### Git workflow

- Feature branches, not direct commits to `main`.
- CI must pass before merge.
- PR descriptions should explain **why**, not just what (the diff shows what).

---

## Adding a feature

Rough playbook:

1. **Is this STRATHEX or STRATHMARK?**
   - If it's math / prediction / Monte Carlo → STRATHMARK first. Get it shipping, then update STRATHEX to use the new API.
   - If it's UI / Excel / tournament workflow → STRATHEX only.

2. **TDD or not?**
   - The STRATHMARK engine uses strict TDD — write the test first, watch it fail, make it pass. 667+ tests and counting.
   - STRATHEX UI code is more exploratory — start with a manual workflow, add tests once the shape stabilizes.

3. **Update docs in the same PR.**
   - Engine change → relevant STRATHMARK wiki page + `docs/SYSTEM_STATUS.md` + if it affects predictions, `explanation_system_functions.py`.
   - Workflow change → relevant STRATHEX wiki page + user-facing docs.

4. **Run the local loop** (lint, test, build).

5. **Open PR.** Link to any related issues; explain the *why*.

---

## Testing matrix

STRATHEX CI runs:

| Job | OS | Python | What |
|---|---|---|---|
| lint | ubuntu-latest | 3.13 | `ruff check . && ruff format --check .` |
| test | ubuntu-latest | 3.13 | `pytest -m "not ollama" --cov=woodchopping` |
| test | windows-latest | 3.13 | Same |
| build | ubuntu-latest | 3.13 | `python -m build && import strathmark` |

Gated by: all four must pass before merge. See [`.github/workflows/ci.yml`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/.github/workflows/ci.yml).

STRATHMARK runs a similar matrix plus a broader Python version range (3.10, 3.12, 3.13) since it's the reusable engine and has more consumers.

---

## Performance benchmarks

For reference on a modern laptop (Apple M2 or Ryzen 7):

| Operation | Time |
|---|---|
| Baseline prediction (8 competitors) | <100ms |
| ML prediction (8 competitors, cached model) | ~200ms |
| LLM prediction (8 competitors, qwen2.5:7b on GPU) | 4–8s |
| LLM prediction (same, CPU only) | 30–60s |
| Monte Carlo 500K × 8 competitors | ~1s |
| Monte Carlo 2M × 10 competitors | ~5s |
| XGBoost retrain (100 records) | ~2s |
| Full handicap calculation (all methods, 8 competitors) | 5–10s |

When optimizing: focus on the LLM layer first. Everything else is already fast.

---

## Release process

STRATHEX doesn't currently publish to PyPI — it's install-from-source. The versioning scheme is:

- **Major (V6)** — breaking architecture changes (e.g., extracting STRATHMARK)
- **Minor (V6.1)** — new tournament formats, significant feature additions
- **Patch (V6.1.2)** — bug fixes, small improvements

STRATHMARK *does* publish to PyPI via `publish.yml`. STRATHEX's `pyproject.toml` pins STRATHMARK's `main` branch directly, so updates flow automatically.

Release checklist:
1. All CI green on a release candidate branch
2. CHANGELOG updated (both repos if engine changed)
3. Version bumped in `pyproject.toml` (both repos)
4. Tag the commit (`git tag v6.1.0 && git push --tags`)
5. Create a GitHub release with the changelog entry

---

## Debugging

### Reproducing a bad handicap

Capture the inputs:

```python
# The exact 8-column representation the engine sees
from woodchopping.strathmark_adapter import dataframe_to_strathmark_inputs
competitors, wood, event_code = dataframe_to_strathmark_inputs(
    selected_competitors_df, wood_species, diameter_mm, quality, event_code
)

# Repro test
import json
with open('repro_inputs.json', 'w') as f:
    json.dump({
        'competitors': [c.to_dict() for c in competitors],
        'wood': wood.to_dict(),
        'event_code': event_code,
    }, f, indent=2)
```

Share the JSON on the issue; the maintainer can replay it against any STRATHMARK version.

### Stepping through a simulation

Monte Carlo is deterministic if you pass a seed:

```python
from strathmark.variance import run_monte_carlo_simulation
results = run_monte_carlo_simulation(
    handicap_results=..., num_simulations=500_000, seed=42
)
```

Same seed → same output, every time. Great for reproducing "why did this win rate change by 0.3%" questions.

---

## Further reading

- [Architecture](Architecture) — module map and data flow
- [Prediction Methods](Prediction-Methods) — engine internals
- [CLAUDE.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/CLAUDE.md) — standing rules for code changes
- [STRATHMARK CONTRIBUTING.md](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/CONTRIBUTING.md) — engine contribution guide
