"""
STRATHEX Analytics Module

This module provides analytical capabilities for competitor performance analysis,
prediction accuracy tracking, and performance profiling.

Modules:
    - performance_history: Historical performance analysis and trend detection (B2)
    - competitor_profiling: Competitor strength/weakness profiling (B4)
    - prediction_accuracy: Prediction accuracy tracking and reporting (B1)
"""

# Import analytics functions
from .competitor_profiling import profile_competitor_strengths
from .performance_history import analyze_performance_history
from .prediction_accuracy import analyze_prediction_accuracy, format_prediction_accuracy_report

__all__ = [
    # Performance history analysis (B2)
    "analyze_performance_history",
    # Competitor profiling (B4)
    "profile_competitor_strengths",
    # Prediction accuracy tracking (B1)
    "analyze_prediction_accuracy",
    "format_prediction_accuracy_report",
]
