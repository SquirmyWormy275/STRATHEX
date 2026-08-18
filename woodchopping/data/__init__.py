"""Data handling module for woodchopping system."""

from woodchopping.data import excel_io as _excel_io
from woodchopping.data.excel_io import (
    append_results_to_excel as _append_results_to_excel,
)
from woodchopping.data.excel_io import (
    detect_results_sheet,
    ensure_workbook,
    get_competitor_id_name_mapping,
    get_species_name_from_code,
    load_competitors_df,
    load_results_df,
    load_wood_data,
    save_time_to_results,
)
from woodchopping.data.preprocessing import (
    calculate_adaptive_half_lives,
    engineer_features_for_ml,
    fit_wood_hardness_index,
    load_and_clean_results,
)
from woodchopping.data.validation import (
    standardize_results_data,
    validate_heat_data,
    validate_results_data,
)
from woodchopping.data.workbook_guard import guarded_append_results_to_excel


def append_results_to_excel(
    heat_assignment_df,
    wood_selection,
    round_object=None,
    tournament_state=None,
    event_name=None,
):
    """Append results while refusing destructive workbook recovery.

    The judge-facing prompts and return contract are unchanged. The guard only
    prevents an unreadable existing workbook from being replaced by a partial
    Results-only file and verifies the workbook after the write.
    """
    return guarded_append_results_to_excel(
        _append_results_to_excel,
        _excel_io,
        heat_assignment_df,
        wood_selection,
        round_object=round_object,
        tournament_state=tournament_state,
        event_name=event_name,
    )


__all__ = [
    # Excel I/O
    "load_competitors_df",
    "load_results_df",
    "load_wood_data",
    "get_competitor_id_name_mapping",
    "get_species_name_from_code",
    "detect_results_sheet",
    "ensure_workbook",
    "save_time_to_results",
    "append_results_to_excel",
    # Validation
    "validate_results_data",
    "validate_heat_data",
    "standardize_results_data",
    # Preprocessing
    "engineer_features_for_ml",
    # Baseline V2 Preprocessing
    "load_and_clean_results",
    "fit_wood_hardness_index",
    "calculate_adaptive_half_lives",
]
