# July branch salvage — October 2026

The old `fix/restore-wood-workbook` tip `22f20e8c0f62bae8b111737a7d596b92140e7d65` is preserved by an archive tag and verified full Git bundles. Its PR merged only an earlier tip. Maintenance recovered applicable later changes onto current main rather than reverting the newer V2/V3 architecture.

| July work | Current disposition |
| --- | --- |
| Fresh-tournament finance choice; pending bracket competitors | Repaired, with actual-menu and renderer regressions |
| Nonpositive selection at seven helper sites and heat entry | Explicit bounds before indexing |
| Roster IDs after row deletion | Preserved IDs; opaque UUID-backed new identities; existing duplicates block writes |
| Payout positions after JSON resume | Restored in the current validated single/multi deserializers; round-trip tests |
| Manual result date | Reject invalid dates and reprompt before any write |
| Wood quality outside 1–10 | Reject and reprompt rather than silently changing it |
| Personal-best result column names | Canonical snake_case results; regression exercises current display |
| Assignment success count | Reports accepted final events |
| ExcelFile handle | Context manager releases the read handle |
| NaN historical diameter | Already guarded by the current STRATHMARK adapter |
| Old championship Mark-3 workaround | Superseded by current selected-engine forecasting; current authority/replay tests cover championship flow |
| Legacy preprocessing, ML features, summary formatting, baseline fit/cache optimizations | Superseded for runtime predictions by STRATHMARK. Retained explicit historical modules and benchmark scripts are not reintroduced as live numeric authority |

Current public prediction exports route to STRATHMARK. The retired baseline optimizer and caches are not the current engine. Existing V2/V3 issue, settlement, recovery, and numeric-authority regressions remain required. The old 126-finding audit is historical evidence, not an automatically accepted current backlog.

The maintenance change also fixes the displayed multi-event menu: 16 shows wood count, 17 saves, and 18 returns. The installed terminal smoke uses a synthetic workbook outside the checkout. No tracked workbook, native DLL, model artifact, rulebook, or signed evidence is removed as cosmetic cleanup.
