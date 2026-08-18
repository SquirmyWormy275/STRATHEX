"""Combine Excel and STRATHMARK ResultStore history for live predictions.

Excel remains the judge-canonical record. The SQLite ResultStore may contain
additional results from earlier competitions, so prediction code consumes the
union while preserving Excel values when the same observation exists in both.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def _normalize_history_frame(frame: Optional[pd.DataFrame]) -> pd.DataFrame:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()

    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    normalized.rename(
        columns={
            "event_code": "event",
            "time_seconds": "raw_time",
            "actual_time": "raw_time",
            "time": "raw_time",
            "diameter_mm": "size_mm",
            "diameter": "size_mm",
            "species_code": "species",
            "result_date": "date",
        },
        inplace=True,
    )

    if "event" in normalized.columns:
        normalized["event"] = normalized["event"].astype(str).str.strip().str.upper()
    if "competitor_name" in normalized.columns:
        normalized["competitor_name"] = normalized["competitor_name"].astype(str).str.strip()
    if "species" in normalized.columns:
        normalized["species"] = normalized["species"].astype(str).str.strip()
    if "heat_id" not in normalized.columns:
        normalized["heat_id"] = ""
    else:
        normalized["heat_id"] = normalized["heat_id"].fillna("").astype(str).str.strip()

    for column in ("raw_time", "size_mm", "quality"):
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    if "date" in normalized.columns:
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")

    return normalized


def merge_result_history(
    excel_results: Optional[pd.DataFrame],
    store_results: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Return the de-duplicated union of Excel and ResultStore observations.

    The ResultStore is populated from Excel on startup, so a simple concatenation
    would duplicate nearly every historical result and distort model training.
    De-duplication mirrors STRATHMARK's store identity:
    competitor + heat + event + raw time. Excel rows are concatenated first and
    retained on collisions because Excel remains the judge-canonical source and
    usually has the more complete date metadata.
    """
    excel = _normalize_history_frame(excel_results)
    store = _normalize_history_frame(store_results)

    if excel.empty:
        return store.reset_index(drop=True)
    if store.empty:
        return excel.reset_index(drop=True)

    combined = pd.concat([excel, store], ignore_index=True, sort=False)

    required = {"competitor_name", "event", "raw_time"}
    if not required.issubset(combined.columns):
        return combined.reset_index(drop=True)

    identity = pd.DataFrame(index=combined.index)
    identity["competitor"] = combined["competitor_name"].astype(str).str.strip().str.casefold()
    identity["event"] = combined["event"].astype(str).str.strip().str.upper()
    identity["time"] = pd.to_numeric(combined["raw_time"], errors="coerce").round(6)
    identity["heat"] = combined["heat_id"].fillna("").astype(str).str.strip().str.casefold()

    duplicate_mask = identity.duplicated(
        subset=["competitor", "heat", "event", "time"],
        keep="first",
    )
    return combined.loc[~duplicate_mask].reset_index(drop=True)
