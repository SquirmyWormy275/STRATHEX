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

A JSON save alone is not a complete V3 backup. Source, model and key changes can
block a saved competition. Preserve older installation profiles when upgrading.

## Resume after an interruption

1. Reopen the original installation with the same workbook and data-directory paths.
2. Use **Load Previous Event/Tournament**.
3. Check the loaded field, engine, issued marks and recorded outcomes.
4. If a V3 command's outcome is uncertain, use its saved command ID and the exact
   retry/recovery action. Do not submit a replacement command with a new identity.

The loader can recover a valid rolling `.bak` if the primary JSON save is damaged.
If both copies are invalid, preserve them and restore a known-good backup.

## Restore into a new directory

Restore the complete set into a private directory and verify it before opening.
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
