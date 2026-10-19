"""Copy the CI-provisioned Python into a private, disposable runner installation.

Hosted tool caches can have shared writable ancestors. Exercise production runtime
checks with a separate protected installation; never relax the application guard
or change permissions on the shared runner cache.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("This provisioning helper is only for disposable GitHub CI runners")
    os.umask(0o077)
    source = Path(sys.base_prefix)
    target = Path.home() / (".strathex-ci-python-" + uuid4().hex)
    target.mkdir(mode=0o700)
    # Dereference the reviewed runner image's links while copying, so the new
    # installation never returns to a mutable shared tool-cache directory.
    shutil.copytree(source, target, symlinks=False, dirs_exist_ok=True)
    executable = target / ("python.exe" if os.name == "nt" else "bin/python3")
    observed = json.loads(
        subprocess.check_output(
            [
                str(executable),
                "-I",
                "-c",
                "import json,sys; print(json.dumps([sys.base_prefix, list(sys.version_info[:2])]))",
            ],
            text=True,
        )
    )
    if Path(observed[0]).resolve() != target.resolve() or observed[1] != [3, 13]:
        raise RuntimeError("Copied CI Python did not retain its separate installation identity")
    with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as stream:
        stream.write(str(executable.parent) + "\n")
        if os.name == "nt":
            stream.write(str(target / "Scripts") + "\n")
    environments = target / "environments"
    environments.mkdir(mode=0o700)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as stream:
        stream.write("STRATHEX_CI_PYTHON=" + executable.as_posix() + "\n")
        stream.write("STRATHEX_CI_ENV_ROOT=" + environments.as_posix() + "\n")
    print("Prepared separate private Python 3.13 for disposable CI environments.")


if __name__ == "__main__":
    main()
