# STRATHEX 7.4.4

This release addresses the October Security Cloud findings and uses the reviewed
STRATHMARK 3.0.0rc12 source for new installations. The numerical prediction rules,
Formula, trained model and per-competition V2/V3 choice are unchanged.

- Spreadsheet exports preserve text, HTML exports escape display values, and
  terminal output removes control sequences.
- HTTP prediction transports verify TLS. The V7 service also requires an
  independently provisioned signer identity.
- Judge approval binds to the current field and mark sheet. Editing a draft
  invalidates its approval; issued marks and completed results cannot be erased
  by setup changes or heat regeneration.
- New event identifiers stay stable when display order changes. Application
  state uses private storage, including independently checked Windows permissions.
- New Linux competition profiles verify the reviewed source and implementation
  pair. Existing saved competitions keep their original runtime, model, keys
  and evidence.

See [the security repair details](SECURITY_CLOUD_2026-10-19.md) for changed operator
requirements, [the runtime contract](CURRENT_RUNTIME_CONTRACT.md) for supported
workflows, and [portable installation](PORTABLE_INSTALLATION.md) for backup,
staging, activation and rollback. Activation requires a verified independent
backup. Staging a new profile does not switch the active installation.

The separate operational V3 service requires an independently provisioned authority
backend. Synthetic CI checks do not establish Windows production qualification.
