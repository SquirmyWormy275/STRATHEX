# STRATHEX v6.0.1 release notes

## What changed

- Single-event and multi-event state saves now use verified temporary files,
  atomic replacement, a rolling `.bak`, nested structure validation, and
  visible backup recovery.
- Heat, semifinal, and final progression now reads only the current appended
  stage. Finals and single-heat events transition to completed state correctly.
- Non-power-of-two bracket byes propagate into the linked next round, and the
  replay suite carries a saved bracket through to a champion without writing
  canonical result stores.
- Multi-event days now explicitly support handicap and championship events;
  bracket competition is directed to the working single-event workflow.
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
  saves fail closed or recover from a valid backup.
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
