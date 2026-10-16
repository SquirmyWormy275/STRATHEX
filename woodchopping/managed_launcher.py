"""Explicit optional shared workspace/process access, without legacy startup."""

from pathlib import Path
from urllib.parse import quote, urlsplit


def workspace_url(base, event_id):
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "Workspace origin must be an HTTPS origin or local loopback origin without credentials, paths, queries or fragments."
        )
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Remote workspaces require HTTPS.")
    if not event_id or len(event_id) > 224 or any(c.isspace() for c in event_id):
        raise ValueError("An existing persistent module event identity is required.")
    return base.rstrip("/") + "/events/" + quote(event_id, safe="")


def run_cli(interpreter, arguments):
    import subprocess

    executable = Path(interpreter).expanduser().absolute()
    if not executable.is_file():
        raise ValueError("Select an installed STRATHMARK interpreter with managed-event support.")
    # The component owns parsing, numerical authority, lifecycle and storage.
    # A failed selected interpreter never falls back to STRATHEX's V2 adapter.
    return subprocess.run([str(executable), "-I", "-m", "strathmark", *arguments], check=False).returncode
