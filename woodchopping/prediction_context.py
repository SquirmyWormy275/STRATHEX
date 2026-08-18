"""Reproducible evidence cutoffs for STRATHMARK field calculations."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, MutableMapping, Optional
from uuid import uuid4

from strathmark.identity import validate_namespaced_identity


def resolve_prediction_as_of(value: Any = None, *, label: str = "prediction_as_of") -> date:
    """Resolve an exclusive cutoff, defaulting to the operator's local event date."""
    if value is None:
        return datetime.now().date()
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).date()
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} must be an ISO date or datetime") from exc
        return resolve_prediction_as_of(parsed, label=label)


def ensure_prediction_as_of(
    state: MutableMapping[str, Any],
    *,
    fallback: Optional[date] = None,
) -> date:
    """Return and persist one exclusive evidence cutoff for an event state."""
    existing = state.get("prediction_as_of")
    if existing is not None:
        cutoff = resolve_prediction_as_of(existing)
    else:
        event_date = state.get("tournament_date") or state.get("date")
        if event_date is not None:
            cutoff = resolve_prediction_as_of(event_date, label="tournament date")
        elif fallback is not None:
            cutoff = resolve_prediction_as_of(fallback, label="fallback")
        else:
            cutoff = resolve_prediction_as_of()
    state["prediction_as_of"] = cutoff.isoformat()

    return cutoff


def ensure_competition_id(state: MutableMapping[str, Any]) -> str:
    """Return and persist one globally distinct STRATHEX competition identity."""
    existing = state.get("competition_id")
    if existing is not None:
        competition_id = validate_namespaced_identity(existing, "competition_id")
    else:
        competition_id = f"strathex:{uuid4()}"
        state["competition_id"] = competition_id
    return competition_id
