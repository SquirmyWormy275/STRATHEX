# STRATHEX v6.0.1 release notes

## What changed

- Single-event and multi-event state saves now use verified temporary files,
  atomic replacement, a rolling `.bak`, nested structure validation, and
  visible backup recovery.
- Heat, semifinal, and final progression now reads only the current appended
  stage. Finals and single-heat events transition to completed state only after
  successful result entry, and both summary paths render single-heat winners.
- Brackets use canonical power-of-two seed positions, so top seeds remain in
  opposite halves while non-power-of-two byes propagate into the linked next
  round. Confirmed bracket matches now autosave and report save failures.
- Multi-event days now explicitly support handicap and championship events;
  bracket competition is directed to the working single-event workflow before
  any canonical Excel or ResultStore write can occur.
- The replay suite now drives the judge-facing multi-event workflow across
  multiple save/reload boundaries, including generated finals and summaries.
- Terminal output normalizes functional symbols and display width. The gallery
  script provides a repeatable Windows visual check and text capture.
- Seven unreachable experimental prediction modules and their unused LightGBM
  and Matplotlib dependencies were removed. Live comparison, seeding, and
  simulator prediction paths remain.
- Package metadata, build artifacts, and the compatibility launcher's banner
  derive v6.0.1 from one canonical version.

## Compatibility

- Existing Excel workbook schemas do not change.
- Existing valid JSON saves continue to load. Structurally malformed primary
  saves, including malformed nested round and bracket match data, fail closed
  or recover from a valid backup.
- `MainProgramV5_2.py` remains the launcher so existing shortcuts keep working.
- STRATHMARK remains pinned at `47bb143`. The evaluated 2.0 release is
  import-compatible but behaviorally incompatible with current STRATHEX.
- Removed prediction modules were private, unreachable, and absent from the
  package's declared public exports. The `v5.2-legacy` branch is the historical
  compatibility record.

## Release evidence

The final tag is gated on the complete isolated non-Ollama suite, Ruff lint and
format checks, a clean wheel import from outside the checkout, a captured
terminal gallery, green hosted CI, and exact-head merge. Final counts and commit
identifiers are recorded in the GitHub release after those gates complete.

This patch release is not a claim of hosted, multi-judge, or general production
readiness.
