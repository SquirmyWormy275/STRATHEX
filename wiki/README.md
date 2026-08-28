# STRATHEX Wiki Source

This directory is the canonical, versioned source for the STRATHEX GitHub wiki. It describes the competition-scoped STRATHMARK V2/V3 selection workflow. V2 remains the production baseline and V3 remains readiness-gated; these pages do not authorize a global V3 cutover.

A repository merge does not update GitHub's separate wiki repository. Publication is a release operation:

1. merge the code and these pages;
2. clone or fetch the `STRATHEX.wiki.git` repository;
3. copy the versioned pages without deleting unrelated wiki metadata;
4. review the wiki diff;
5. push the wiki commit;
6. fetch the public wiki again and verify its HEAD and page contents.

Do not publish pre-release semantics as current. Dated release pages in `docs/` remain the evidence for older versions.
