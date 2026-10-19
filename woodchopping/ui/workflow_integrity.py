"""Preserve official evidence and bind draft mark approval to its exact inputs."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

_CONTEXT_KEYS = (
    "wood_species",
    "wood_diameter",
    "wood_quality",
    "event_code",
    "event_type",
    "prediction_as_of",
    "prediction_authority_ref",
    "num_stands",
    "format",
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def field_context_digest(state, root_state=None):
    """Bind ordered stable IDs, names, wood, cutoff and competition authority."""
    context = {key: state.get(key) for key in _CONTEXT_KEYS}
    frame = state.get("all_competitors_df")
    identities = {}
    if frame is not None and hasattr(frame, "iterrows"):
        for _, row in frame.iterrows():
            identities[str(row.get("competitor_name", ""))] = str(row.get("competitor_id", row.get("CompetitorID", "")))
    context["competitors"] = [(str(name), identities.get(str(name), "")) for name in state.get("all_competitors", [])]
    context["competitor_status"] = state.get("competitor_status", {})
    if root_state is not None:
        context["prediction_authority_ref"] = root_state.get("prediction_authority_ref")
        context["root_prediction_as_of"] = root_state.get("prediction_as_of")
    return _digest(context)


def _sheet_digest(rows):
    return _digest([{k: v for k, v in row.items() if k not in {"approved_by", "approved_at"}} for row in rows])


def protect_evidence(state):
    """Reject destructive setup changes once official or V3 lifecycle evidence exists."""
    if any(state.get(key) for key in ("actual_results", "results", "finish_order")) or any(
        state.get("final_results", {}).values()
    ):
        raise ValueError("Official results must be preserved through the result correction workflow.")
    if state.get("status") in {"in_progress", "completed"}:
        raise ValueError("Competition has started; retain its field and use the result correction workflow.")
    for key, value in state.items():
        if key.startswith("v3_") and value:
            raise ValueError("V3 lifecycle evidence exists; retain this field and use its recovery workflow.")
    for row in state.get("handicap_results_all", []):
        if row.get("issued_mark") or row.get("receipt_id"):
            raise ValueError("Issued or receipted marks must be retained through recovery.")
    for round_object in state.get("rounds", []):
        if round_object.get("status") in {"in_progress", "completed"} or any(
            round_object.get(key) for key in ("actual_results", "results", "finish_order", "issued")
        ):
            raise ValueError("Recorded or issued rounds cannot be replaced by a setup change.")
        for row in round_object.get("handicap_results", []):
            if row.get("issued_mark") or row.get("receipt_id"):
                raise ValueError("Issued or receipted marks must be retained through recovery.")


def _archive(value):
    if isinstance(value, pd.DataFrame):
        return {"columns": list(value.columns), "records": value.to_dict(orient="records")}
    if isinstance(value, dict):
        return {key: _archive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_archive(item) for item in value]
    return copy.deepcopy(value)


def invalidate_draft(state, *, reason, root_state=None):
    """Archive draft artifacts before clearing every dependent current-use pointer."""
    protect_evidence(state)
    keys = ("handicap_results_all", "rounds", "schedule", "mark_approval", "calculation_context_digest")
    prior = {key: _archive(state[key]) for key in keys if state.get(key)}
    if prior:
        state.setdefault("superseded_drafts", []).append(
            {
                "reason": reason,
                "at": datetime.now(timezone.utc).isoformat(),
                "artifacts": prior,
            }
        )
    state["handicap_results_all"] = []
    state["rounds"] = []
    state.pop("mark_approval", None)
    state.pop("calculation_context_digest", None)
    if "schedule" in state:
        state["schedule"] = []
    state["current_round_index"] = 0
    if prior:
        state["status"] = "configured"
    if root_state is not None and root_state.get("schedule"):
        root_state.setdefault("superseded_schedules", []).append(_archive(root_state["schedule"]))
        root_state["schedule"] = []


def prepare_field_change(state, *, reason, root_state=None):
    """Check all fields before changing any of them; report a safe UI rejection."""
    events = state.get("events", [state])
    try:
        protect_evidence(root_state or state)
        for event in events:
            protect_evidence(event)
        for event in events:
            invalidate_draft(event, reason=reason, root_state=root_state or state)
    except ValueError as error:
        print(f"\n[BLOCKED] {error}")
        return False
    return True


def bind_calculation(state, root_state=None):
    state["calculation_context_digest"] = field_context_digest(state, root_state)
    state.pop("mark_approval", None)


def require_current_calculation(state, root_state=None):
    expected = state.get("calculation_context_digest")
    if not expected or expected != field_context_digest(state, root_state):
        raise ValueError("Field or wood changed, or this saved sheet predates context validation. Recalculate first.")


def approve_marks(state, initials, timestamp, *, root_state=None):
    require_current_calculation(state, root_state)
    if state.get("status") == "completed" or any(
        item.get("status") == "in_progress" or (item.get("status") != "completed" and item.get("actual_results"))
        for item in state.get("rounds", [])
    ):
        raise ValueError("Started or completed marks require the result correction workflow.")
    if not initials or not str(initials).strip() or not timestamp or not state.get("handicap_results_all"):
        raise ValueError("A complete mark sheet, judge identity and approval time are required.")
    state["mark_approval"] = {
        "judge": str(initials).strip(),
        "at": str(timestamp),
        "context_digest": field_context_digest(state, root_state),
        "sheet_digest": _sheet_digest(state["handicap_results_all"]),
    }


def require_approved_marks(state, *, include_rounds=True, root_state=None):
    require_current_calculation(state, root_state)
    approval = state.get("mark_approval", {})
    rows = state.get("handicap_results_all", [])
    if (
        not rows
        or not approval.get("judge")
        or not approval.get("at")
        or (
            approval.get("context_digest") != field_context_digest(state, root_state)
            or approval.get("sheet_digest") != _sheet_digest(rows)
        )
    ):
        raise ValueError("Review and approve the current marks in View Handicaps before official use.")
    if not include_rounds:
        return
    approved = {_sheet_digest([row]) for row in rows}
    for round_object in state.get("rounds", []):
        if round_object.get("status") == "completed":
            continue
        marks = round_object.get("handicap_results", [])
        if len(marks) != len(round_object.get("competitors", [])) or any(
            _sheet_digest([row]) not in approved for row in marks
        ):
            raise ValueError("Scheduled marks differ from the approved sheet; regenerate and review the field.")


def new_event_id():
    return "event_" + uuid4().hex


def require_removable_event(tournament, event):
    """Only an unreferenced draft can be physically removed; identities never shift."""
    protect_evidence(event)
    if any(event.get(key) for key in ("all_competitors", "rounds", "handicap_results_all", "superseded_drafts")):
        raise ValueError("This event has assignments or calculation history and must be retained.")
    identity = event["event_id"]

    def references(value):
        if isinstance(value, dict):
            return identity in value or any(references(item) for item in value.values())
        if isinstance(value, (tuple, list)):
            return any(references(item) for item in value)
        return isinstance(value, str) and (value == identity or identity in value)

    other_state = {key: value for key, value in tournament.items() if key != "events"}
    if references(other_state) or any(references(item) for item in tournament.get("events", []) if item is not event):
        raise ValueError("Entries, fees, schedules or receipts reference this event; it must be retained.")
