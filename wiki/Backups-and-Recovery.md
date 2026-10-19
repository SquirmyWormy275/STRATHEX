# Back up and recover a competition

## Before an event or upgrade

Make an independent copy of the workbook and operator-data directory. Keep the
application version and selected engine with the saved competition. Check that
you can read the backup before removing an older copy.

For Linux V3, the configured recovery directory must already exist on a different
filesystem from the live workbook. Runtime command archives and workbook recovery
copies are verified before acknowledgment or export.

## What to keep

| Competition | Recovery set |
| --- | --- |
| V2 | Workbook, JSON saves and rolling backups, ResultStore, engine-selection records and original application/dependency version. |
| Linux V3 | Everything above, plus command ledger, signed receipts, runtime database and separate head, signing key/identity, frozen histories, trained model and exact runtime/wheels. |

A JSON save alone is not a complete backup for either engine: keep the private
installation authority database that binds its bytes and original path as well. Source, model and key changes can
block a saved competition. Preserve older installation profiles when upgrading.

## Resume after an interruption

1. Reopen the original installation with the same workbook and data-directory paths.
2. Use **Load Previous Event/Tournament**.
3. Check the loaded field, engine, issued marks and recorded outcomes.
4. If a V3 command's outcome is uncertain, use its saved command ID and the exact
   retry/recovery action. Do not submit a replacement command with a new identity.

From 7.4.5, loading requires the exact save bytes recorded in the private installation
authority store. An edited, missing, historical or unbound save stops; a `.bak` is
preserved for reviewed recovery and is never automatically promoted. Keep both copies
and the original private database. Resume a historical competition through its original
retained profile where compatible, including 7.4.4/rc12 or 7.4.2/rc7. Do not edit JSON
or reset the authority database to bypass the block. A complete independently verified
recovery is required when the original profile cannot resume.

## Restore into a new directory

Preserve a complete copy in a private recovery directory and verify it before opening.
Save authority binds original paths; copying JSON into a new profile does not migrate
that evidence or make it loadable. Retain the original profile and use independently
reviewed recovery for path/authority changes.
For Linux V3, keep authority directories at mode 700 and key, identity, database
and head files at mode 600. Never initialize a replacement signing key over an
existing competition or edit its database to bypass a recovery block.

Use the [Linux recovery runbook](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/V3_LINUX_COMPETITION.md)
for the exact restore checks. The
[portable installation guide](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PORTABLE_INSTALLATION.md)
covers selecting retained profiles and rollback. Rollback selects an old installation;
it does not rewrite a saved competition.

## Encrypted archives

The optional GPG policy encrypts recovery archives and verifies full decryption
before reporting success. Keep a protected recovery-key copy independently of the
workstation and archive drive. A fingerprint or public key cannot decrypt the archive.

Retain plaintext copies until encrypted readback and recovery-key storage are
verified. The portable guide covers policy setup, filesystem requirements and
retrying interrupted archive publication.


Later encrypted `verify` operations require an independently retained plaintext SHA256,
never a value from the neighboring unsigned receipt. A public-key holder can produce
new ciphertext and matching receipt hashes. Without independent evidence, `inspect`
only reports integrity and cannot authorize restore. Large archives need a source- or
inventory-owned size allowance. Existing encryption keys and archives remain readable;
see the [release-paired recovery helper guide](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/PORTABLE_INSTALLATION.md#745-independent-recovery-identity).
