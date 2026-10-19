# STRATHEX 7.4.6

This maintenance release addresses nine findings from the verification scan of
7.4.5. New profiles use the reviewed STRATHMARK 3.0.0rc14 security source. Handicap
mathematics, the V2 calculation contract, Formula and trained model are unchanged.

- V3 rehearsal cannot write official results or export official start schedules.
  The eligible local competition adapter requires issued receipt rows before
  collecting results, then settles and checkpoints before workbook export.
- Reviewed competitor IDs must match the live workbook both before result entry
  and at the canonical write. A later name-to-ID reassignment stops without a
  workbook or ResultStore result write and restores uncommitted in-memory results.
- Official text schedules visibly escape line, bidirectional and invisible
  controls. Names remain unchanged in stored competition records.
- Imported workbooks use bounded snapshots before spreadsheet parsing. JSON saves
  are limited to 16 MiB before reading or parsing. All workbook writers require
  protected ancestry and use exclusive private staging, synchronization and an
  unchanged-original check before atomic publication.
- Portable installation requires an independently acquired manifest SHA256 before
  parsing or installing. The trusted bootstrap pins its exact recovery helper.
  Selected managed, preview and local competition interpreters retain virtual
  environment behavior while protected runtime inputs are checked before execution.
- Browser workspace links require HTTPS, including loopback, with a trusted server
  certificate. A local port alone does not establish server identity.

Keep all original profiles, including 7.4.5/rc13, 7.4.4/rc12 and 7.4.2/rc7, for
saved competitions. Stage the new profile separately and retain independent,
verified encrypted recovery before activation. Source recognition does not migrate
old evidence or confer Windows V7 production qualification.

See the [finding dispositions](SECURITY_CLOUD_FINAL_VALIDATION_2026-10-19.md),
[portable installation guide](PORTABLE_INSTALLATION.md) and
[current runtime contract](CURRENT_RUNTIME_CONTRACT.md).
