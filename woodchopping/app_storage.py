"""Provision only the dedicated directory selected for application state."""

from __future__ import annotations

import os
from pathlib import Path

from strathmark.private_storage import private_directory, reject_links, verify_private_directory

IS_WINDOWS = os.name == "nt"


def prepare_data_directory(path: Path, *, workbook: Path | None = None) -> Path:
    directory = reject_links(path)
    if directory in (Path.home(), *Path.home().parents) or (directory / ".git").exists():
        raise ValueError("Choose a dedicated STRATHEX data subdirectory outside the home or checkout root")
    if workbook is not None and directory == workbook.expanduser().absolute().parent:
        raise ValueError("Keep the dedicated STRATHEX data directory separate from the workbook directory")
    if directory.exists() and any(directory.iterdir()):
        # Saved data never authorizes changing access to surrounding files.
        # Previously private Windows installations can be reopened unchanged.
        if IS_WINDOWS:
            verify_private_directory(directory)
        return directory
    return private_directory(directory)
