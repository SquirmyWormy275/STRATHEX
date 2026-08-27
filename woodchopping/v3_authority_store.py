"""Durable local command/ack ledger for STRATHMARK V3 HTTP operations."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class V3CommandRecord:
    command_key: str
    operation: str
    method: str
    path: str
    request_digest: str
    request_json: str
    state: str
    response_json: str | None
    error_code: str | None

    @property
    def request(self) -> dict[str, Any]:
        value = json.loads(self.request_json)
        if not isinstance(value, dict):
            raise RuntimeError("stored V3 command request is not an object")
        return value

    @property
    def response(self) -> dict[str, Any] | None:
        if self.response_json is None:
            return None
        value = json.loads(self.response_json)
        if not isinstance(value, dict):
            raise RuntimeError("stored V3 command response is not an object")
        return value


class V3CommandStore:
    """SQLite authority for pending, acknowledged, and ambiguous V3 commands."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS v3_commands (
                    command_key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','acknowledged','recovery_required','rejected')),
                    response_json TEXT,
                    error_code TEXT
                )""")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def begin(
        self,
        *,
        command_key: str,
        operation: str,
        method: str,
        path: str,
        request_digest: str,
        request_json: str,
    ) -> V3CommandRecord:
        with self._connect() as connection:
            existing = connection.execute("SELECT * FROM v3_commands WHERE command_key = ?", (command_key,)).fetchone()
            if existing is not None:
                record = self._record(existing)
                if record.request_digest != request_digest or record.operation != operation:
                    raise ValueError("V3 command identity is already bound to different input")
                return record
            connection.execute(
                "INSERT INTO v3_commands VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)",
                (command_key, operation, method, path, request_digest, request_json),
            )
        return self.get(command_key)

    def acknowledge(self, command_key: str, response: dict[str, Any]) -> None:
        encoded = json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                "UPDATE v3_commands SET state='acknowledged', response_json=?, error_code=NULL WHERE command_key=?",
                (encoded, command_key),
            )

    def mark_recovery_required(self, command_key: str, error_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE v3_commands SET state='recovery_required', error_code=? WHERE command_key=?",
                (error_code, command_key),
            )

    def reject(self, command_key: str, error_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE v3_commands SET state='rejected', error_code=? WHERE command_key=?",
                (error_code, command_key),
            )

    def get(self, command_key: str) -> V3CommandRecord:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM v3_commands WHERE command_key = ?", (command_key,)).fetchone()
        if row is None:
            raise KeyError(command_key)
        return self._record(row)

    @staticmethod
    def _record(row: sqlite3.Row) -> V3CommandRecord:
        return V3CommandRecord(**dict(row))


__all__ = ["V3CommandRecord", "V3CommandStore"]
