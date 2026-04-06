"""
Prediction models for woodchopping competition times.

This module provides three prediction methods:
1. Baseline - Statistical predictions using historical averages
2. ML - XGBoost machine learning models (separate SB/UH models)
3. LLM - AI-enhanced predictions with quality adjustments via Ollama

The prediction_aggregator module combines all three methods and selects
the best prediction using priority logic: ML > LLM > Baseline
"""

# LLM Integration
# AI Predictor (LLM-based)
from woodchopping.predictions.ai_predictor import (
    predict_competitor_time_with_ai,
)

# Baseline Predictions
from woodchopping.predictions.baseline import (
    backtest_baseline_predictions,
    get_competitor_historical_times_flexible,
    get_competitor_historical_times_normalized,
    get_event_baseline_flexible,
    predict_baseline_time,
)

# Check My Work Validation
from woodchopping.predictions.check_my_work import (
    check_my_work,
    display_check_my_work,
)
from woodchopping.predictions.llm import (
    call_ollama,
    check_ollama_connection,
    reset_ollama_status,
)

# ML Model
from woodchopping.predictions.ml_model import (
    display_feature_importance,
    perform_cross_validation,
    predict_time_ml,
    train_ml_model,
)

# Prediction Aggregator
from woodchopping.predictions.prediction_aggregator import (
    display_dual_predictions,
    generate_prediction_analysis_llm,
    get_all_predictions,
    select_best_prediction,
)

__all__ = [
    # LLM Integration
    "call_ollama",
    "check_ollama_connection",
    "reset_ollama_status",
    # Baseline Predictions
    "get_competitor_historical_times_flexible",
    "get_competitor_historical_times_normalized",
    "get_event_baseline_flexible",
    "predict_baseline_time",
    "backtest_baseline_predictions",
    # ML Model
    "train_ml_model",
    "predict_time_ml",
    "perform_cross_validation",
    "display_feature_importance",
    # AI Predictor
    "predict_competitor_time_with_ai",
    # Prediction Aggregator
    "get_all_predictions",
    "select_best_prediction",
    "generate_prediction_analysis_llm",
    "display_dual_predictions",
    # Check My Work
    "check_my_work",
    "display_check_my_work",
]
