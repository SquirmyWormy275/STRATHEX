---
title: Excel Results sheet must follow the 8-column strict schema — column-order writes corrupt named columns silently
date: 2026-04-21
category: data-integrity
module: data
problem_type: database_issue
component: database
symptoms:
  - "Quality column populated with strings like 'Heat 1/Heat 2' (HeatID values in the wrong column)"
  - "Quality column mostly null with the non-null values being unusable strings — ML features and baseline normalization couldn't use it"
  - "detect_results_sheet() created headers in one order; append_results_to_excel() wrote values in a different order"
root_cause: logic_error
resolution_type: code_fix
severity: high
related_components:
  - tooling
tags: [excel, openpyxl, schema, column-order, data-corruption, results-sheet]
---

# Excel Results sheet must follow the 8-column strict schema — column-order writes corrupt named columns silently

## Problem
In January 2026, a data audit discovered the `Quality` column in `woodchopping.xlsx` contained strings like `"Heat 1/Heat 2"` instead of integers 0–10. Values intended for the `HeatID` column were landing in `Quality` because the writer (`append_results_to_excel()`) and the schema detector (`detect_results_sheet()`) disagreed on column order. The writer was inserting values positionally; the schema expected named columns in a specific order; the mismatch meant every row written for months had quality contaminated with text.

No crash. No warning. ML features trained on this field were silently useless, and baseline normalization that tried to multiply by `Quality` either skipped those rows or coerced the string to NaN.

## Symptoms
- `Quality` column has strings like `"Heat 1/Heat 2"` or round identifiers instead of integers
- ML models show the quality feature has near-zero importance (because the data is garbage)
- `pd.to_numeric(df["Quality"], errors="coerce")` produces many NaNs from rows that should have valid quality values
- Spot-checking `woodchopping.xlsx` by hand shows values that look like `HeatID` entries in the `Quality` column

## What Didn't Work
- Writing with pandas `df.to_excel()`. It produces correct column ordering but is not atomic — it rewrites the whole sheet, which is slow, prone to corruption on concurrent writes, and loses formatting
- Patching the writer to reorder on the fly. The writer was never the authoritative source — the schema detector was. Patching the writer alone leaves the detector in its old state, so the next `detect_results_sheet()` run undoes the fix
- Adding a validation check that coerces `Quality` to int. Masks the symptom, preserves the underlying column-order mismatch

## Solution
**Canonicalize on a strict 8-column schema and enforce it in both the detector and the writer.**

```
Column 1: CompetitorID
Column 2: Event
Column 3: Time
Column 4: Size            (diameter in mm)
Column 5: Species Code
Column 6: Quality         (0–10 int)
Column 7: HeatID
Column 8: Date
```

- `detect_results_sheet()` validates the header row against this exact order. If headers are missing, wrong, or in the wrong order, it refuses to operate and surfaces a clear error to the user
- `append_results_to_excel()` writes by column *name* against the detected header, not by positional index. If a column is missing from the sheet, it raises rather than silently dropping the value
- Excel I/O uses `openpyxl` (not `pandas.to_excel`) for atomic cell-level appends — see [woodchopping/data/excel_io.py](../../../woodchopping/data/excel_io.py)

## Why This Works
**Positional writes are a footgun for any schema that evolves.** The original code worked when the schema was fixed; it broke the moment a column was added, renamed, or reordered. Named writes decouple the writer from column ordering — the header row is the contract, and the writer looks up by name.

**openpyxl atomic append avoids a second class of corruption.** `pandas.to_excel` reads the entire sheet, modifies it in memory, and writes it back. If anything happens between the read and the write (the judge force-closes Python, Windows autosaves Excel, a Supabase sync task runs concurrently), the file can end up truncated or missing data. `openpyxl` appends one row to the live sheet and commits immediately — the failure window is a single cell write, not an entire file rewrite.

## Prevention
- When adding a new column to the Results sheet, update `detect_results_sheet()` *and* `append_results_to_excel()` *and* the `_DATA_DEPENDENT_TESTS` allowlist in [tests/conftest.py](../../../tests/conftest.py) in the same commit. Use grep on the new column name to confirm every touch point is updated
- Never write to the Results sheet positionally. Always look up column index by header name at write time
- Never use `pandas.to_excel()` for appending to a production sheet. Reserve pandas for read-only analysis and temp files
- Validate new rows with a schema check before the write — at minimum: `CompetitorID` is non-empty, `Time` is a positive float, `Quality` is an int in [0, 10]
- When the schema changes in a way that might corrupt historical data (column rename, type change), write a one-off migration script that rewrites the file atomically, then delete the script. Do not ship the migration as part of the normal writer — it should be an explicit, auditable step
- Add a CI test (or at least a manual audit) that reads a sample fixture sheet and asserts the expected columns exist in the expected positions. This would have caught the original bug in seconds

## Related Issues
- [CLAUDE.md "Excel operations should use openpyxl, not pandas to_excel"](../../../CLAUDE.md)
- [woodchopping/data/excel_io.py](../../../woodchopping/data/excel_io.py) — current writer and detector
- [wiki/Data-Model.md](../../../wiki/Data-Model.md) — judge-facing description of the Results sheet columns
- [docs/SYSTEM_STATUS.md](../../SYSTEM_STATUS.md) — data model summary
