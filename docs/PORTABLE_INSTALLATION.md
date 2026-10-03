# Portable Linux installations and rollback

STRATHEX 7.4 supplies `scripts/install_portable.py`, a standard-library Linux bootstrap. A private release bundle contains `release.json`, complete SHA256-pinned wheel sets for two Python 3.13 environments, and the operator's exact Formula/ML candidate. Models and workbook history stay outside the public repository and GitHub releases. The public installer does not contain trained weights or operator data.

The app environment keeps the unchanged STRATHMARK V2 source at `a231ad65fe82317516cc82a282761d73adb0c0e3`. The runtime environment contains the separately reviewed V3 wheel. Installation checks every file before provisioning, uses offline wheels without dependency resolution, and verifies installed runtime/model/Formula identities and package versions. New profiles use separate saved-data and signing-authority directories. Installation errors leave the previous active profile selected.

```bash
python3 scripts/install_portable.py install \
  --bundle /private/strath-release \
  --workbook /operator/woodchopping.xlsx \
  --backup-dir /independent-disk/recovery \
  --uv /path/to/uv
python3 scripts/install_portable.py list
python3 scripts/install_portable.py launch
python3 scripts/install_portable.py runtime -- status
python3 scripts/install_portable.py rollback
python3 scripts/install_portable.py activate strathex-7.4.1-strathmark-3.0.0rc6-release-reviewed
```

The installation home defaults to `~/.local/share/strath/installations`; use `--home /private/location` before the operation to choose another. Selection and rollback first create an independent archive of profile descriptors, workbooks, saved competitions, command outboxes and signing-authority files. Every regular member is read back and checked against its source SHA256, and a dated verification record explains the change. Adopted profiles retain their original paths; their external data and authority directories are included too. The backup location must be on a different filesystem from both the installation and every retained workbook or authority. Archives are created with owner-only mode 0600 from their first byte on filesystems that support POSIX permissions; removable filesystems such as some NTFS mounts may not enforce that mode, so their physical/access permissions determine confidentiality. Never discard the exact old environments, trained model, signing keys or saved data after upgrading.

The launcher holds a profile lock for the application's entire lifetime. Close STRATHEX before changing the active profile. To resume an older saved competition, launch its original profile explicitly:

```bash
python3 scripts/install_portable.py launch --profile linux-competition-7.3.2
```

Rollback selects the previous verified profile. It preserves later profiles and their competition history. It does not downgrade or rewrite a competition under another source identity. Both V2 and V3 remain deliberate per-competition choices. An existing competition never changes its selected engine because the active installation changes.

Before making a new installation the normal launcher, verify the actual installed app outside a checkout, the engine selector, the full approval/issue/results/restart workflow, and a restored independent backup. The release bundle's SHA256 list verifies bytes; it is not a digital signature or a grant of Windows CNG qualification. Obtain the installer and release manifest from the reviewed release, and keep private bundle backups independently.

Every launch rechecks the recorded interpreter, V2/app/V3 program files, import hooks, Formula, signing identity and model bytes. Profile-managed paths cannot be replaced by trailing command arguments. A missing inference model blocks new forecasts; explicit retained lifecycle operations and result corrections may continue with unchanged authority and source identity. Changing present model bytes is always refused. Selecting the already active profile preserves its previous rollback target.

## 7.4.1 encrypted recovery support

The retained rc6 private profile is `strathex-7.4.1-strathmark-3.0.0rc6-release-reviewed`. Keep previous profiles for saved competitions; their exact source bindings cannot be upgraded in place. The bootstrap ships with its byte-matched `recovery_security.py` companion. An optional private `recovery-encryption-policy.json` in the installation home enables GPG-encrypted profile-switch archives and, for profiles declaring `backup_encryption_supported`, native competition backups. The policy format and authenticated recovery checks are documented in the [STRATHMARK Linux runbook](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/V3_LINUX_COMPETITION.md). A policy never upgrades retained older binaries: their native archives use their original format. Preserve plaintext legacy archives until encryption readback and an independent protected recovery-key copy are verified. Public wheels and installer assets contain no keys, workbook results or trained weights.

`install --stage-only` provisions and verifies a new profile without changing the active selection. It can retain the intended archive path while the drive is unavailable; activation and launch still enforce the independent-backup prerequisite. Use `activate RELEASE_ID` after the drive is recognized. Staging is not proof of a durable backup.

Encrypted archives publish through a locked private temporary file. Full authenticated readback finishes before the final ciphertext appears; interrupted publication can be retried without overwriting a completed archive. The verification receipt alone is not a completed backup.

Encrypted recovery requires hard-link support for atomic publication without overwriting an existing archive. The bootstrap checks this capability before staging an activation/rollback archive and before launching an encrypted competition profile. Filesystems without hard links, including exFAT, are rejected before an archive starts. Use an independent filesystem that passes the check.

## 7.4.2 buffered recovery

The new profile is `strathex-7.4.2-strathmark-3.0.0rc7-recovery-reviewed`. The helper uses bounded bulk input/output through GPG pipes, avoiding tiny direct filesystem operations on large removable-drive archives. Complete authenticated readback and no-overwrite publication are unchanged. Retained rc6 competitions use their exact old runtime; the rc6 prospective protocol also requires that original implementation. New profiles cannot silently replace either identity. See [7.4.2 release notes](RELEASE_v7.4.2.md).
