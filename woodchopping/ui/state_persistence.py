"""Crash-safe persistence for single-event and multi-event tournament state.

The original UI modules wrote JSON directly over the active save file. An
interrupted write could therefore destroy the only recoverable tournament
state. This module preserves the existing public functions and messages while
adding same-directory temporary files, fsync, validation, atomic replacement,
a rolling last-known-good backup, and automatic backup recovery.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

JsonValidator = Callable[[Any], None]


def _json_default(value: Any) -> Any:
    """Convert NumPy/pandas values while retaining the legacy string fallback."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory sync after an atomic rename."""
    if os.name == "nt":
        return
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        fd = os.open(str(directory), flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_valid_json(path: Path, validator: JsonValidator) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    validator(payload)
    return payload


def _write_temp_file(directory: Path, prefix: str, text: str) -> Path:
    fd, temp_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _copy_file_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    temp_path = Path(temp_name)
    try:
        with source.open("rb") as input_handle, os.fdopen(fd, "wb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.replace(temp_path, destination)
        _fsync_directory(destination.parent)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _atomic_write_json(
    payload: Any,
    filename: str,
    validator: JsonValidator,
) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        default=_json_default,
    )
    parsed = json.loads(text)
    validator(parsed)

    temp_path = _write_temp_file(path.parent, path.name + ".", text)
    backup = _backup_path(path)
    previous_was_valid = False

    try:
        if path.exists():
            try:
                _read_valid_json(path, validator)
                previous_was_valid = True
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                previous_was_valid = False

            if previous_was_valid:
                _copy_file_atomically(path, backup)

        os.replace(temp_path, path)
        _fsync_directory(path.parent)

        try:
            _read_valid_json(path, validator)
        except Exception:
            if previous_was_valid and backup.exists():
                _copy_file_atomically(backup, path)
            raise
    finally:
        temp_path.unlink(missing_ok=True)


def _load_with_recovery(filename: str, validator: JsonValidator) -> Any:
    path = Path(filename)
    backup = _backup_path(path)

    try:
        return _read_valid_json(path, validator)
    except FileNotFoundError as primary_error:
        if not backup.exists():
            raise primary_error
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as primary_error:
        if not backup.exists():
            raise primary_error

    payload = _read_valid_json(backup, validator)
    _copy_file_atomically(backup, path)
    print(f"[WARN] Recovered tournament state from backup: {backup}")
    return payload


def _validate_single_state(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Tournament state must be a JSON object")
    if "rounds" in payload and not isinstance(payload["rounds"], list):
        raise ValueError("Tournament state 'rounds' must be a list")
    if "all_competitors" in payload and not isinstance(payload["all_competitors"], list):
        raise ValueError("Tournament state 'all_competitors' must be a list")
    if "all_competitors_df" in payload and not isinstance(payload["all_competitors_df"], list):
        raise ValueError("Tournament state 'all_competitors_df' must be a list")


def _validate_multi_state(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Multi-event tournament state must be a JSON object")
    if "events" not in payload or not isinstance(payload["events"], list):
        raise ValueError("Multi-event tournament state requires an 'events' list")
    if "total_events" in payload and not isinstance(payload["total_events"], int):
        raise ValueError("Multi-event tournament state 'total_events' must be an integer")


def _serialize_single_state(tournament_state: Dict[str, Any]) -> Dict[str, Any]:
    state_copy = copy.deepcopy(tournament_state)

    competitors_df = state_copy.get("all_competitors_df")
    if isinstance(competitors_df, pd.DataFrame):
        state_copy["all_competitors_df"] = competitors_df.to_dict("records")
    elif competitors_df is None:
        state_copy["all_competitors_df"] = []

    for round_object in state_copy.get("rounds", []):
        competitors = round_object.get("competitors_df")
        if isinstance(competitors, pd.DataFrame):
            round_object["competitors_df"] = competitors.to_dict("records")
        elif competitors is None:
            round_object["competitors_df"] = []

    _validate_single_state(state_copy)
    return state_copy


def _deserialize_single_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(payload)
    state["all_competitors_df"] = pd.DataFrame(state.get("all_competitors_df") or [])

    for round_object in state.get("rounds", []):
        round_object["competitors_df"] = pd.DataFrame(round_object.get("competitors_df") or [])

    state.setdefault("payout_config", None)
    return state


def _serialize_multi_state(tournament_state: Dict[str, Any]) -> Dict[str, Any]:
    state_copy = copy.deepcopy(tournament_state)

    roster_df = state_copy.get("competitor_roster_df")
    if isinstance(roster_df, pd.DataFrame):
        state_copy["competitor_roster_df"] = roster_df.to_dict("records")

    for event in state_copy.get("events", []):
        competitors_df = event.get("all_competitors_df")
        if isinstance(competitors_df, pd.DataFrame):
            event["all_competitors_df"] = competitors_df.to_dict("records")

        for round_object in event.get("rounds", []):
            round_df = round_object.get("competitors_df")
            if isinstance(round_df, pd.DataFrame):
                round_object["competitors_df"] = round_df.to_dict("records")

    _validate_multi_state(state_copy)
    return state_copy


def _deserialize_multi_state(payload: Dict[str, Any]) -> Dict[str, Any]:
    tournament_state = copy.deepcopy(payload)

    roster_df = tournament_state.get("competitor_roster_df")
    if isinstance(roster_df, list):
        tournament_state["competitor_roster_df"] = pd.DataFrame(roster_df)

    for event in tournament_state.get("events", []):
        competitors_df = event.get("all_competitors_df")
        if isinstance(competitors_df, list):
            event["all_competitors_df"] = pd.DataFrame(competitors_df)

        for round_object in event.get("rounds", []):
            round_df = round_object.get("competitors_df")
            if isinstance(round_df, list):
                round_object["competitors_df"] = pd.DataFrame(round_df)

        event.setdefault("event_type", "handicap")
        event.setdefault("payout_config", None)
        event.setdefault(
            "competitor_status",
            {name: "active" for name in event.get("all_competitors", [])},
        )

    if "tournament_roster" not in tournament_state:
        all_competitors: set[str] = set()
        for event in tournament_state.get("events", []):
            all_competitors.update(event.get("all_competitors", []))
        tournament_state["tournament_roster"] = [
            {
                "competitor_name": name,
                "competitor_id": "",
                "events_entered": [],
                "entry_fees_paid": {},
            }
            for name in sorted(all_competitors)
        ]
        tournament_state["entry_fee_tracking_enabled"] = False
        tournament_state["competitor_roster_df"] = pd.DataFrame()

    return tournament_state


def save_tournament_state(
    tournament_state: Dict[str, Any],
    filename: str = "saves/tournament_state.json",
) -> None:
    """Atomically save single-event tournament state with a rolling backup."""
    try:
        payload = _serialize_single_state(tournament_state)
        _atomic_write_json(payload, filename, _validate_single_state)
        print(f"Tournament state saved to {filename}")
    except Exception as error:
        print(f"Error saving tournament state: {error}")


def load_tournament_state(filename: str = "saves/tournament_state.json") -> Optional[Dict[str, Any]]:
    """Load single-event state, recovering the last valid backup when needed."""
    try:
        payload = _load_with_recovery(filename, _validate_single_state)
        state = _deserialize_single_state(payload)
        print(f"Tournament state loaded from {filename}")
        return state
    except FileNotFoundError:
        print(f"Tournament state file '{filename}' not found.")
        return None
    except Exception as error:
        print(f"Error loading tournament state: {error}")
        return None


def auto_save_state(tournament_state: Dict[str, Any]) -> None:
    save_tournament_state(tournament_state, "saves/tournament_state.json")


def save_multi_event_tournament(
    tournament_state: Dict[str, Any],
    filename: str = "saves/multi_tournament_state.json",
) -> None:
    """Atomically save multi-event state with a rolling backup."""
    try:
        payload = _serialize_multi_state(tournament_state)
        _atomic_write_json(payload, filename, _validate_multi_state)
        print(f"\n[OK] Tournament state saved to {filename}")
    except Exception as error:
        print(f"\n[WARN] Error saving tournament state: {error}")


def load_multi_event_tournament(
    filename: str = "saves/multi_tournament_state.json",
) -> Optional[Dict[str, Any]]:
    """Load multi-event state, recovering the last valid backup when needed."""
    try:
        payload = _load_with_recovery(filename, _validate_multi_state)
        tournament_state = _deserialize_multi_state(payload)
        print(f"\n[OK] Tournament state loaded from {filename}")
        print(f"[OK] Tournament: {tournament_state.get('tournament_name', 'Unknown')}")
        print(f"[OK] Events: {tournament_state.get('total_events', 0)}")
        return tournament_state
    except FileNotFoundError:
        print(f"\n[WARN] Tournament file '{filename}' not found")
        return None
    except Exception as error:
        print(f"\n[WARN] Error loading tournament state: {error}")
        return None


def auto_save_multi_event(tournament_state: Dict[str, Any]) -> None:
    save_multi_event_tournament(tournament_state, "saves/multi_tournament_state.json")


def install_persistence_guards() -> None:
    """Replace legacy direct-write functions without altering their call sites."""
    tournament_ui = importlib.import_module("woodchopping.ui.tournament_ui")
    multi_event_ui = importlib.import_module("woodchopping.ui.multi_event_ui")

    if getattr(tournament_ui, "_atomic_state_persistence_installed", False):
        return

    tournament_ui.save_tournament_state = save_tournament_state
    tournament_ui.load_tournament_state = load_tournament_state
    tournament_ui.auto_save_state = auto_save_state
    tournament_ui._atomic_state_persistence_installed = True

    multi_event_ui.save_multi_event_tournament = save_multi_event_tournament
    multi_event_ui.load_multi_event_tournament = load_multi_event_tournament
    multi_event_ui.auto_save_multi_event = auto_save_multi_event
    multi_event_ui._atomic_state_persistence_installed = True
