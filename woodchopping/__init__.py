"""
Woodchopping Handicap Management System

A comprehensive system for calculating fair handicaps in woodchopping competitions
using STRATHMARK v2 predictions and Monte Carlo simulation.
"""

__version__ = "7.0.0"
__author__ = "STRATHEX Project"

# Import key components for easy access
from woodchopping.data.excel_io import (
    get_competitor_id_name_mapping,
    load_competitors_df,
    load_results_df,
    load_wood_data,
)
from woodchopping.data.preprocessing import engineer_features_for_ml
from woodchopping.data.validation import validate_results_data

# Live handicap calculations are exposed through ``woodchopping.handicaps``;
# package-level exports remain limited to stable data utilities.

__all__ = [
    # Data
    "load_competitors_df",
    "load_results_df",
    "load_wood_data",
    "get_competitor_id_name_mapping",
    "validate_results_data",
    "engineer_features_for_ml",
]
