# Complete local Linux V3 competitions

STRATHEX 7.3.0 offers the separate STRATHMARK 3.0.0rc4 Linux competition profile. Select V2 or V3 explicitly at the competition root; children inherit it and the first numeric action locks the choice. Linux V3 displays `LINUX READY` and records mode `local`. It runs actual Formula + trained CatBoost, pooling, capability adjustment, and complete-field optimization. The LLM council is unavailable, so fields require degraded or individual judge review. Windows V7 production qualification remains a separate installation gate.

Install V2/STRATHEX and V3 in separate Python 3.13 environments. Keep the reviewed V2 dependency intact. Supply an authorized, verified trained ML bundle, and keep models and private history outside the repository. Follow STRATHMARK's [full runtime, model, policy, and recovery runbook](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/V3_LINUX_COMPETITION.md).

```bash
strathex --workbook /operator/competition.xlsx --data-dir /operator/strathex-data \
  --local-v3-python /path/to/v3/bin/python \
  --local-v3-ml-bundle /private/operator/ml-bundle \
  --local-v3-runtime-root /private/operator/v3-authority \
  --local-v3-backup-dir /independent-disk/recovery
```

Use a new data directory for new local competitions; saved preview or V7 scopes retain their original profiles and exact environments. The operator recovery directory must exist on a different filesystem from the live workbook. Runtime command archives and workbook recovery copies are verified before acknowledgment/export. Preserve the installation key, SQLite log/head, frozen history, model, exact wheels, and STRATHEX saves and authority/command ledgers together. Missing models block new predictions while retained issue, settlement, and exact retry remain available.

The judge workflow is: mark-free seeding → actual heats/stands → complete proposed field → explicit approval → separate **Issue these approved marks now?** confirmation → official sheet → complete outcome entry → settlement → next round → competition closure. Declining issue retains an approved unissued field. Printing and results are blocked until issue acknowledgment. Championship fields receive signed fixed Mark 3 receipts.

Confirmed ID-bound outcomes and exact settlement requests are saved before submission. Authorize the judge's official placings, preserving ties. Enter raw seconds, DNF, DQ, DNS, VOID, or `PENALTY <raw seconds> <penalty seconds>` for every issued competitor. Nonfinishes and penalties stay outside raw-time training history. Complete all fields in that event's prior round before advancing; separate events advance independently, and a direct heat-to-final transition uses the next actual round ordinal. Same-round heats retain the frozen epoch; later rounds use valid completed results and earned scores. Source/model/key changes block existing scopes instead of silently changing their predictions or falling back to V2.

For an official correction, rerun the same launcher and add `--correct-v3-results /operator/strathex-data/saves/tournament_state.json`. Select the settled field, enter a reason and complete revised outcomes. This appends a signed revision, reverses superseded predictive scores, preserves prior observations and issued marks, and retains frozen epochs and saved advancement. Excel retains superseded raw values outside active history. Current saved times and official placings reflect the accepted revision. Review advancement separately after an official correction.

`python scripts/smoke_linux_competition.py --v3-python /path/to/v3/bin/python --ml-bundle /private/operator/ml-bundle --output /new/synthetic-smoke-directory` verifies the installed consumer, real inference, approval/issue distinction, explicit outcomes, restart, later-round changes, championship receipts, corrections, and closure with synthetic workbook data. Never run a test against an operator workbook.
