"""Helpers for checking competitor history and capturing manual results entry."""

from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

from woodchopping.data import save_time_to_results, standardize_results_data
from woodchopping.data.validation import check_competitor_eligibility


def competitor_has_event_history(results_df: pd.DataFrame, competitor_name: str, event_code: str) -> bool:
    """Return True if competitor has any results for the event."""
    if results_df is None or results_df.empty:
        return False
    if not competitor_name:
        return False
    event_code = str(event_code).strip().upper()
    results_df, _ = standardize_results_data(results_df)
    comp_match = (
        results_df["competitor_name"].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    )
    event_match = results_df["event"].astype(str).str.strip().str.upper() == event_code
    return not results_df[comp_match & event_match].empty


def filter_competitors_with_history(
    comp_df: pd.DataFrame, results_df: pd.DataFrame, event_code: str
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Filter roster to only competitors meeting minimum data requirements.

    Returns (eligible_df, blocked_names)
    - eligible_df: Competitors with N >= 3 results (may have warnings for N < 10)
    - blocked_names: Competitors with N < 3 (absolute minimum)
    """
    if comp_df is None or comp_df.empty:
        return comp_df, []
    if "competitor_name" not in comp_df.columns:
        return pd.DataFrame(), []

    event_code = str(event_code).strip().upper()
    results_df, _ = standardize_results_data(results_df)

    eligible = []
    blocked = []

    for _, row in comp_df.iterrows():
        name = row.get("competitor_name")
        if not name:
            continue

        # Check eligibility using NEW sparse data validation
        is_eligible, message, count = check_competitor_eligibility(results_df, name, event_code)

        if is_eligible:
            eligible.append(row)
            # Store warning message in row if needed (for display later)
            if message:  # Has warning (N < 10)
                row_copy = row.copy()
                row_copy["_warning"] = message
                row_copy["_result_count"] = count
                eligible[-1] = row_copy
        else:
            blocked.append(name)

    if eligible:
        eligible_df = pd.DataFrame(eligible)
    else:
        eligible_df = pd.DataFrame(columns=comp_df.columns)

    return eligible_df, blocked


def prompt_add_competitor_times(competitor_name: str, event_code: str, wood_info: Dict[str, any]) -> bool:
    """
    Prompt judge to add historical times for a competitor and append to Results sheet.

    Returns True if at least one time was recorded.
    """
    event_code = str(event_code).strip().upper()
    species = wood_info.get("species")
    diameter = wood_info.get("size_mm")
    quality = wood_info.get("quality", 5)

    if not species or not diameter:
        print("\n[WARN] Wood selection incomplete. Cannot add times without species and diameter.")
        return False

    print("\nEnter historical times for this competitor.")
    print("Press Enter with no input when finished.")

    added_any = False
    while True:
        raw = input("  Time (seconds): ").strip()
        if raw == "":
            break
        try:
            time_val = float(raw)
        except ValueError:
            print("  Invalid time. Try again.")
            continue

        date_input = input("  Date (YYYY-MM-DD) or blank for today: ").strip()
        if date_input:
            timestamp = date_input
        else:
            timestamp = datetime.now().isoformat(timespec="seconds")

        heat_id = f"MANUAL-{event_code}"
        save_time_to_results(
            event=event_code,
            name=competitor_name,
            species=species,
            size=diameter,
            quality=quality,
            time=time_val,
            heat_id=heat_id,
            timestamp=timestamp,
        )
        added_any = True
        print("  [OK] Added")

    return added_any
