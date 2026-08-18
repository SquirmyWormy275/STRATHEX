# STRATHEX Wiki Source

This directory is the canonical, versioned source for the STRATHEX GitHub wiki. It describes STRATHEX 7.0.0 and STRATHMARK 2.0.0.

A repository merge does not update GitHub's separate wiki repository. Publication is a release operation:

1. merge the code and these pages;
2. clone or fetch the `STRATHEX.wiki.git` repository;
3. copy the versioned pages without deleting unrelated wiki metadata;
4. review the wiki diff;
5. push the wiki commit;
6. fetch the public wiki again and verify its HEAD and page contents.

Do not publish pre-release semantics as current. Dated release pages in `docs/` remain the evidence for older versions.
