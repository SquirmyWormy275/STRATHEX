"""Read-only protection for explicitly selected, separately installed Python runtimes.

Keep the venv entry point: resolving it for execution would discard its packages.
Trusted ownership and non-writable ancestry prevent another account from swapping
checked files before spawn. Identity changes within the owner's environment stop
an already configured client instead of silently selecting a different runtime.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _status(path):
    value = path.lstat()
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _trusted(path, *, directory=False, symlink=False, ancestor=False):
    """Inspect ownership/access without tightening any selected or shared path."""
    from strathmark.private_storage import reject_links

    reject_links(path.parent)
    if os.name == "nt":
        from strathmark.private_storage import _windows

        # This read-only check accepts owner/admin/system installation files,
        # and rejects peer modification without changing their DACLs.
        if ancestor and directory:
            # An ancestor's create-child right does not modify an existing
            # protected child. Actual importable directories below stay strict.
            _windows().verify_ancestors(path / ".runtime-child-check")
        else:
            _windows().verify_ancestors(path, include_tool_input=True)
    else:
        value = path.lstat()
        if value.st_uid not in (0, os.geteuid()) or (
            not symlink and value.st_mode & 0o022 and not (ancestor and directory and value.st_mode & stat.S_ISVTX)
        ):
            raise PermissionError(f"Selected runtime is writable by another account: {path}")
        # Sticky ancestry protects existing owned names, but a runtime cannot
        # use a directly shared directory for importable files or hooks.
        if not directory and path.parent.stat().st_mode & 0o022:
            raise PermissionError(f"Selected runtime parent is shared: {path.parent}")
    value = path.lstat()
    expected = stat.S_ISLNK if symlink else (stat.S_ISDIR if directory else stat.S_ISREG)
    if not expected(value.st_mode) or getattr(value, "st_file_attributes", 0) & 0x400:
        raise PermissionError(f"Selected runtime contains an unsupported path: {path}")
    return _status(path)


def _resolved(path, identity, links=()):
    """Resolve only for inspection, retaining every protected link in identity."""
    if path.parent == path:
        _trusted(path, directory=True, ancestor=True)
        return path
    parent = _resolved(path.parent, identity, links)
    candidate = parent / path.name
    if candidate.is_symlink():
        if candidate in links or len(links) >= 40:
            raise ValueError("Selected runtime contains a cyclic interpreter link")
        target = os.readlink(candidate)
        identity[str(candidate)] = _trusted(candidate, symlink=True) + (target,)
        target = Path(target)
        absolute = Path(os.path.abspath(target if target.is_absolute() else parent / target))
        return _resolved(absolute, identity, (*links, candidate))
    _trusted(candidate, directory=candidate.is_dir(), ancestor=True)
    return candidate


def _tree(root):
    inventory = {}
    for directory, folders, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        _trusted(parent, directory=True)
        for name in folders:
            _trusted(parent / name, directory=True)
        for name in files:
            path = parent / name
            links = {}
            checked = _resolved(path, links) if path.is_symlink() else path
            inventory.update(links)
            identity = _trusted(checked)
            # CPython may populate caches after a successful guarded spawn.
            # Their permissions are still checked; only those derived cache
            # bytes are omitted from the stable installation identity.
            if "__pycache__" not in path.parts:
                inventory[str(checked)] = identity
    return inventory


class TrustedPython:
    """Capture a protected venv before its first execution, then recheck it."""

    def __init__(self, executable):
        self.executable = Path(executable).expanduser().absolute()
        self.identity = self._capture()

    def _capture(self):
        identity = {}
        selected = self.executable
        root = _resolved(selected.parent.parent, identity)
        if selected.parent.name.lower() not in {"bin", "scripts"} or not (root / "pyvenv.cfg").is_file():
            raise ValueError("Select a separately installed Python virtual environment")
        # Ordinary venv/uv symlinks are supported, but every selected name and
        # target must have trusted ancestry. Execute self.executable unchanged.
        path = _resolved(selected, identity)
        identity[str(path)] = _trusted(path)
        entry_directory = _resolved(selected.parent, identity)
        identity.update(_tree(entry_directory))
        if not os.access(path, os.X_OK):
            raise PermissionError("Selected Python runtime is not executable")
        configuration = root / "pyvenv.cfg"
        identity[str(configuration)] = _trusted(configuration)
        if configuration.stat().st_size > 16_384:
            raise ValueError("Selected runtime configuration exceeds its size limit")
        settings = {}
        for line in configuration.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                settings[key.strip().lower()] = value.strip()
        if settings.get("include-system-site-packages", "false").lower() != "false":
            raise ValueError("Selected runtime must isolate its installed packages")
        sites = [root / "Lib" / "site-packages", *root.glob("lib/python*/site-packages")]
        sites = [site for site in sites if site.exists()]
        if len(sites) != 1:
            raise ValueError("Selected runtime must have one separate site-packages directory")
        identity.update(_tree(sites[0]))
        # The base executable and standard library are still trusted inputs to
        # a venv. Do not execute Python to discover them before checking them.
        home = Path(settings.get("home", ""))
        if not home.is_absolute():
            raise ValueError("Selected runtime must name its absolute base installation")
        home = _resolved(home, identity)
        _trusted(home, directory=True)
        libraries = [home / "Lib", home / "DLLs", *home.parent.glob("lib/python*")]
        for library in libraries:
            if library.is_dir():
                identity.update(_tree(library))
            elif library.is_file():
                identity[str(library)] = _trusted(library)
        for pattern in ("python*.dll", "python*.zip", "*._pth"):
            for adjacent in home.glob(pattern):
                identity[str(adjacent)] = _trusted(adjacent)
        if os.name == "posix":
            for pattern in ("libpython*.so*", "libpython*.dylib"):
                for library in (home.parent / "lib").glob(pattern):
                    # Shared builds load this sibling of the stdlib. Preserve
                    # both protected link names and the actual library bytes.
                    resolved = _resolved(library, identity)
                    identity[str(resolved)] = _trusted(resolved)
        return identity

    def verify(self):
        if self._capture() != self.identity:
            raise ValueError("Selected Python installation changed after configuration; reopen its original profile")
        return self.executable
