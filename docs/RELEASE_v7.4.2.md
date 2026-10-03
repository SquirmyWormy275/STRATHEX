# STRATHEX 7.4.2 recovery maintenance

The separate Linux profile coordinates STRATHMARK 3.0.0rc7 with a byte-identical standalone GPG recovery helper. Input and output use bounded 1 MiB filesystem operations through pipes. Full authenticated GPG completion, source stability, member hashes and receipt-first no-overwrite publication remain required. Failed processing joins the input feeder and stops GPG. No persistent ciphertext cache is created.

V2/V3 selection remains deliberate per competition. Retain earlier profiles and use their original code/model/signing identities for saved competitions; do not replace installed files in place. This patch changes recovery implementation identity and creates a separate profile for new competitions.

The current numerical model and Formula remain unchanged. Two additional TRAIN/TUNE-only sparse-history experiments failed to beat the existing model. Historical workbook versions did not supply the 20 missing dates; possible repeated rows still require original heat/round confirmation. No source rows were deleted or corrected. See the [accuracy record](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/ACCURACY_AND_COUNCIL.md).

The pre-existing prospective protocol stays pinned to the original rc6 implementation and requires 100 genuinely later results from ten new competitions. Keep that retained profile for the comparison. Encrypted recovery still needs an independent protected offline recovery-key copy before plaintext archives can be retired. Windows CNG qualification is unchanged.
