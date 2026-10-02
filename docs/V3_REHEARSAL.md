# STRATHEX V3 rehearsal setup

STRATHEX V3 operation is rehearsal-only. Its reviewed service source is `ba056ed84cad845af408da11556d5b171e737f68`, consumer contract `strathmark.v3-consumer-contract.v7`, and OpenAPI SHA-256 `20174ab13d32c74419e90bfdc73e6b5d5e3e888e1a6cf098f20e585c3bf2ec24`. Installing current STRATHMARK main is not a substitute for that exact service identity. V2 continues to use its separate pinned library.

Create separate Python 3.13 environments for the STRATHEX consumer and STRATHMARK service. Install the service's exact authorized wheel and `requirements/v3-release.lock`. Configure its event database, artifact roots, authenticated service principal, source-bound identity, pre-field signer, and injected forecast/lifecycle services according to [STRATHMARK deployment](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/DEPLOYMENT.md). There is intentionally no zero-configuration V3 global ASGI app. `uvicorn strathmark.api:app` starts V2, not V3.

For the consumer, configure absolute paths and one loopback endpoint:

```bash
export STRATHMARK_V3_BASE_URL=http://127.0.0.1:8787
export STRATHMARK_V3_BUNDLE_ID=reviewed-installed-bundle-id
export STRATHMARK_V3_CREDENTIAL_ENV=STRATHMARK_V3_SERVICE_CREDENTIAL
export STRATHMARK_V3_CONTRACT_DIGEST=20174ab13d32c74419e90bfdc73e6b5d5e3e888e1a6cf098f20e585c3bf2ec24
export STRATHMARK_V3_SOURCE_COMMIT=ba056ed84cad845af408da11556d5b171e737f68
export STRATHEX_V3_COMMAND_DB=/absolute/path/to/rehearsal/v3_commands.db
export STRATHEX_PREDICTION_AUTHORITY_DB=/absolute/path/to/rehearsal/prediction_authority.db
export STRATHMARK_DB_PATH=/absolute/path/to/rehearsal/v2_results.db
```

Replace the bundle placeholder with the reviewed installed bundle identity. There is no default credential reference. Inject the service credential into `STRATHMARK_V3_SERVICE_CREDENTIAL` through the installation's secret mechanism; the client reads the variable named by `STRATHMARK_V3_CREDENTIAL_ENV`. Alternatively configure both `STRATHMARK_V3_CREDENTIAL_KEYRING_SERVICE` and `STRATHMARK_V3_CREDENTIAL_KEYRING_ACCOUNT` for the OS keyring. Never put credentials in tracked files or URLs. Confirm authenticated status reports the exact reviewed source and contract plus a valid pre-field signer binding before selecting V3.

Use a copied workbook and a new data directory. Launch `strathex --workbook /absolute/path/to/copied.xlsx --data-dir /absolute/path/to/rehearsal`. Choose V3 deliberately at the competition root. It should remain visibly rehearsal-only even if the service advertises production-ready evidence.

Rehearse setup and tournament inheritance, mark-free seeding, exact fields, green/amber batch and red review, immutable approval acknowledgments, official issue acknowledgment, result settlement, next-round epochs, restart, and exact-command recovery. Keep the workbook, JSON saves, authority database, command database, and service evidence together. An ambiguous command remains blocked until a deliberate retry; never choose V2 as an automatic fallback inside that scope.

Linux can run the consumer and V2 library/API. Portable V3 tests and replay run on Python 3.13, but the reviewed production native optimizer, capacity evidence, and non-exportable CNG signing installation remain Windows-specific. A Linux portable run does not provision that production installation.

## Installed synthetic pair check

Build STRATHEX 7.1.1 and STRATHMARK 3.0.0rc1 wheels from their clean reviewed sources. The service checkout must be exactly `ba056ed84cad845af408da11556d5b171e737f68`. With Python 3.13, run:

```bash
python scripts/smoke_v3_pair.py \
  --service-checkout /absolute/path/to/STRATHMARK \
  --service-source ba056ed84cad845af408da11556d5b171e737f68 \
  --consumer-wheel dist/strathex-7.1.1-py3-none-any.whl \
  --service-wheel /absolute/path/to/STRATHMARK/dist/strathmark-3.0.0rc1-py3-none-any.whl \
  --output /absolute/path/to/installed-v3-pair.json
```

The script creates and removes two isolated environments and synthetic service/consumer databases. Use Windows paths on Windows. Alternatively, provide both `--consumer-python` and `--service-python` for existing separate installed environments. Installed files must match the supplied wheels, and the service environment must match every entry in its release lock. The clean service checkout supplies only reviewed test fixtures and public artifacts; application code loads from installed packages.

The report names its wheel and fixture digests and declares `evidence_tier=synthetic_development_key` and `authority_changed=false`. It exercises real HTTP, signed no-mark forecasts, exact fields, distinct approval/issue, response loss after a committed settlement, and recovery from a new consumer process. Test cards and settlement reactions do not prove model execution, next-round capability updates, or production eligibility. The designated installation rehearsal in issue 16 remains required.
