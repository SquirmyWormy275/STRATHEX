# STRATHEX 7.4.5

This follow-up to the October Security Cloud scans strengthens save, approval,
installation, workbook and recovery boundaries. New installations pair with
STRATHMARK 3.0.0rc13; handicap mathematics, V2's calculation contract, Formula,
trained model and deliberate per-competition engine selection remain unchanged.

The app pins the [exact reviewed rc13 source](https://github.com/SquirmyWormy275/STRATHMARK/commit/f064d67abe4baf7672239a14796c0bdc4f8c2071).
Publication requires that commit to remain in merged main with the same source
tree; the installed engine must also match its reviewed implementation digest.

- Complete save bytes must match private installation-held evidence. Historical,
  changed or unbound saves and rolling backups stop for recovery review without
  automatic activation or rewriting.
- Multi-event V2 schedules, official exports and results require judge approval
  bound to the current sheet. Edited or later-round marks need fresh review.
- Wheel and model installation consumes an exclusive private, verified snapshot.
  Shared or linked installation/profile ancestry is refused before execution;
  existing nonempty data directories are checked without changing their permissions.
- Linux V3 result identifiers remain literal spreadsheet text. Workbook publication
  uses an exclusive private temporary file and checks both staged and original file
  identities before replacement. Managed event links use canonical identifiers.
- Later encrypted recovery verification requires an independently trusted plaintext
  SHA256. Legacy integrity inspection is explicitly separate. GPG input/output and
  processing time are bounded; trusted source/inventory allowances preserve large
  backups without accepting receipt-declared budget increases.

Keep the complete original 7.4.4/rc12 and 7.4.2/rc7 profiles for their saved
competitions. Stage the new profile separately; it does not migrate historical
JSON, source identities, signing keys or active competition data. Resume an older
profile where compatible or independently review recovery. Existing ciphertext and
keys remain readable. No immutable release asset or historical profile is replaced.

See the [eight finding dispositions and recovery constraints](SECURITY_CLOUD_FOLLOWUP_2026-10-19.md),
[current runtime contract](CURRENT_RUNTIME_CONTRACT.md) and
[portable installation guide](PORTABLE_INSTALLATION.md). Verified HTTPS and V7
signer provisioning remain mandatory; Windows production qualification and the
separate operational V3 witness remain independent installation requirements.
