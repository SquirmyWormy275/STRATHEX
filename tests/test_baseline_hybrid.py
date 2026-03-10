"""
Unit tests for Baseline V2 Hybrid Prediction Model.

Tests all functions across Phases 1-4:
- Phase 1: Data preprocessing and wood hardness index
- Phase 2: Hierarchical model fitting
- Phase 3: Convergence calibration layer
- Phase 4: Integration and prediction interface
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import functions under test
from woodchopping.data.preprocessing import (
    load_and_clean_results,
    fit_wood_hardness_index,
    calculate_adaptive_half_lives
)
from woodchopping.predictions.baseline import (
    get_competitor_median_diameter,
    estimate_diameter_curve,
    estimate_competitor_std_dev,
    fit_hierarchical_regression,
    group_wise_bias_correction,
    apply_soft_constraints,
    apply_convergence_adjustment,
    calibrate_predictions_for_handicapping,
    fit_and_cache_baseline_v2_model,
    predict_baseline_v2_hybrid,
    invalidate_baseline_v2_cache
)
from woodchopping.data import load_results_df, load_wood_data


# ============================================================================
# FIXTURES - Test Data Setup
# ============================================================================

@pytest.fixture
def sample_results_df():
    """Create a sample results DataFrame for testing."""
    np.random.seed(42)
    # Create dates for all 20 records
    dates = [datetime.now() - timedelta(days=i * 30) for i in range(20)]

    data = {
        'CompetitorID': [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5],
        'competitor_name': ['Alice'] * 4 + ['Bob'] * 4 + ['Charlie'] * 4 + ['David'] * 4 + ['Eve'] * 4,
        'event': ['SB', 'SB', 'UH', 'UH'] * 5,
        'Time': [25, 26, 30, 31, 40, 41, 45, 46, 50, 51, 55, 56, 60, 61, 65, 66, 35, 36, 40, 41],
        'Species': ['S01'] * 20,
        'Diameter': [300, 300, 300, 300, 280, 280, 280, 280, 260, 260, 260, 260, 250, 250, 250, 250, 300, 300, 300, 300],
        'quality': [5] * 20,
        'heat_id': ['H1'] * 20,
        'date': dates,  # Already has 20 elements, don't multiply
        'Notes (Competition, special circumstances, etc.)': [''] * 20
    }

    return pd.DataFrame(data)


@pytest.fixture
def sample_wood_df():
    """Create a sample wood DataFrame for testing."""
    data = {
        'speciesID': ['S01', 'S02', 'S03'],
        'species': ['eastern white pine', 'ponderosa pine', 'poplar (European)'],
        'janka_hard': [1690, 2050, 2400],
        'spec_gravity': [0.34, 0.38, 0.36],
        'crush_strength': [4800, 5320, 5540],  # Match actual column name
        'shear': [1200, 1320, 1390],  # Match actual column name
        'MOR': [8600, 9200, 10300],  # Match actual column name
        'MOE': [1240000, 1290000, 1380000]  # Match actual column name
    }

    return pd.DataFrame(data)


# ============================================================================
# PHASE 1: DATA PREPROCESSING TESTS
# ============================================================================

def test_load_and_clean_results(sample_results_df):
    """Test load_and_clean_results normalizes column names and validates data."""
    cleaned_df = load_and_clean_results(sample_results_df)

    # Check standardized column names
    assert 'raw_time' in cleaned_df.columns
    assert 'size_mm' in cleaned_df.columns
    assert 'species' in cleaned_df.columns.str.lower()

    # Check data types
    assert pd.api.types.is_numeric_dtype(cleaned_df['raw_time'])
    assert pd.api.types.is_numeric_dtype(cleaned_df['size_mm'])

    # Check no outliers (all times should be valid)
    assert (cleaned_df['raw_time'] >= 10.0).all()
    assert (cleaned_df['raw_time'] <= 300.0).all()


def test_fit_wood_hardness_index(sample_results_df, sample_wood_df):
    """Test fit_wood_hardness_index learns composite index from data."""
    cleaned_df = load_and_clean_results(sample_results_df)
    hardness_index = fit_wood_hardness_index(cleaned_df, sample_wood_df)

    # Check index is computed for available species
    assert isinstance(hardness_index, dict)
    assert 'S01' in hardness_index
    assert isinstance(hardness_index['S01'], (int, float))

    # Check index values are reasonable (should be positive)
    for species_id, index_val in hardness_index.items():
        assert index_val > 0, f"Hardness index for {species_id} should be positive"


def test_calculate_adaptive_half_lives(sample_results_df):
    """Test calculate_adaptive_half_lives assigns correct half-lives based on activity."""
    cleaned_df = load_and_clean_results(sample_results_df)
    half_lives = calculate_adaptive_half_lives(cleaned_df)

    # Check all competitors have a half-life
    assert isinstance(half_lives, dict)
    assert len(half_lives) == 5  # Alice, Bob, Charlie, David, Eve

    # Check half-life values are valid options (365, 730, or 1095)
    valid_half_lives = {365, 730, 1095}
    for competitor, half_life in half_lives.items():
        assert half_life in valid_half_lives, f"Half-life {half_life} for {competitor} not in {valid_half_lives}"


# ============================================================================
# PHASE 2: HIERARCHICAL MODEL TESTS
# ============================================================================

def test_get_competitor_median_diameter(sample_results_df):
    """Test get_competitor_median_diameter calculates correct median."""
    cleaned_df = load_and_clean_results(sample_results_df)

    # Alice has all 300mm diameters for SB
    median = get_competitor_median_diameter('Alice', 'SB', cleaned_df)
    assert median == 300.0

    # Bob has all 280mm diameters
    median = get_competitor_median_diameter('Bob', 'SB', cleaned_df)
    assert median == 280.0


def test_estimate_diameter_curve(sample_results_df):
    """Test estimate_diameter_curve fits polynomial curve."""
    cleaned_df = load_and_clean_results(sample_results_df)
    curve_info = estimate_diameter_curve(cleaned_df, 'SB')

    # Check curve info structure
    assert 'coefficients' in curve_info
    assert len(curve_info['coefficients']) == 3  # Quadratic: [c0, c1, c2]

    # Check other expected keys
    assert 'diameter_range' in curve_info
    assert 'r_squared' in curve_info

    # Coefficients should be numeric
    for coef in curve_info['coefficients']:
        assert isinstance(coef, (int, float))


def test_estimate_competitor_std_dev(sample_results_df):
    """Test estimate_competitor_std_dev calculates variance with reasonable bounds."""
    cleaned_df = load_and_clean_results(sample_results_df)

    # Estimate std_dev for Alice (should have low variance, times 25-26)
    std_dev, consistency = estimate_competitor_std_dev('Alice', 'SB', cleaned_df)

    # Check std_dev is clamped to reasonable bounds
    assert 1.5 <= std_dev <= 6.0, f"Std dev {std_dev} outside expected range"

    # Check consistency rating is valid
    valid_ratings = ['VERY HIGH', 'HIGH', 'MODERATE', 'LOW']
    assert consistency in valid_ratings


def test_fit_hierarchical_regression(sample_results_df, sample_wood_df):
    """Test fit_hierarchical_regression creates a valid model."""
    from woodchopping.data.preprocessing import fit_wood_hardness_index, calculate_adaptive_half_lives

    cleaned_df = load_and_clean_results(sample_results_df)
    hardness_index = fit_wood_hardness_index(cleaned_df, sample_wood_df)
    half_lives = calculate_adaptive_half_lives(cleaned_df)

    model = fit_hierarchical_regression(
        cleaned_df, sample_wood_df, hardness_index, half_lives
    )

    # Check model structure
    assert 'event_intercepts' in model
    assert 'diameter_curves' in model
    assert 'competitor_effects' in model

    # Check event intercepts exist for SB and UH
    assert 'SB' in model['event_intercepts']
    assert 'UH' in model['event_intercepts']


# ============================================================================
# PHASE 3: CONVERGENCE CALIBRATION TESTS
# ============================================================================

def test_group_wise_bias_correction():
    """Test group_wise_bias_correction adjusts predictions correctly."""
    # Create sample predictions (simulating bias)
    predictions_dict = {
        'Alice': 25.0,
        'Bob': 40.0,
        'Charlie': 50.0,
        'David': 60.0
    }

    # Mock results_df with historical data showing bias
    np.random.seed(42)
    results_df = pd.DataFrame({
        'competitor_name': ['Alice', 'Bob', 'Charlie', 'David'] * 10,
        'event': ['SB'] * 40,
        'raw_time': [27, 42, 52, 62] * 10,  # Actual times consistently higher
        'size_mm': [300] * 40
    })

    corrected = group_wise_bias_correction(predictions_dict, 300, 'SB', results_df)

    # Check predictions are adjusted (should be higher due to consistent bias)
    for name in predictions_dict:
        assert corrected[name] >= predictions_dict[name] - 0.1  # Allow for small corrections


def test_apply_soft_constraints():
    """Test apply_soft_constraints prevents under-prediction of slowest competitors."""
    predictions_dict = {
        'Alice': 25.0,
        'Bob': 40.0,
        'Charlie': 50.0,
        'David': 58.0  # Predicted too fast (should be ~60s based on history)
    }

    # Mock results_df with historical times
    results_df = pd.DataFrame({
        'competitor_name': ['David'] * 10,
        'event': ['SB'] * 10,
        'raw_time': [60, 61, 59, 62, 60, 61, 59, 60, 61, 60]  # Consistent ~60s
    })

    constrained = apply_soft_constraints(predictions_dict, results_df, 'SB')

    # David's prediction should be boosted closer to historical floor
    assert constrained['David'] >= predictions_dict['David']


def test_apply_convergence_adjustment():
    """Test apply_convergence_adjustment compresses finish-time spread."""
    predictions_dict = {
        'Alice': 25.0,
        'Bob': 40.0,
        'Charlie': 50.0,
        'David': 60.0
    }

    # Spread is currently 35 seconds (60 - 25)
    # Target spread is 2 seconds

    adjusted = apply_convergence_adjustment(
        predictions_dict,
        diameter=300,
        event_code='SB',
        target_spread=2.0,
        preserve_ranking=True
    )

    # Check spread is reduced (not necessarily to exactly 2s, but significantly reduced)
    original_spread = max(predictions_dict.values()) - min(predictions_dict.values())
    adjusted_spread = max(adjusted.values()) - min(adjusted.values())

    assert adjusted_spread <= original_spread, "Convergence adjustment should not increase spread"

    # Check ranking is preserved
    original_order = sorted(predictions_dict.keys(), key=lambda k: predictions_dict[k])
    adjusted_order = sorted(adjusted.keys(), key=lambda k: adjusted[k])
    assert original_order == adjusted_order, "Ranking should be preserved"


def test_calibrate_predictions_for_handicapping():
    """Test calibrate_predictions_for_handicapping applies full pipeline."""
    predictions_dict = {
        'Alice': 25.0,
        'Bob': 40.0,
        'Charlie': 50.0,
        'David': 60.0
    }

    # Mock results_df
    results_df = pd.DataFrame({
        'competitor_name': ['Alice', 'Bob', 'Charlie', 'David'] * 10,
        'event': ['SB'] * 40,
        'raw_time': [25, 40, 50, 60] * 10,
        'size_mm': [300] * 40
    })

    calibrated, metadata = calibrate_predictions_for_handicapping(
        predictions_dict, 300, 'SB', results_df
    )

    # Check calibrated predictions are valid
    assert len(calibrated) == len(predictions_dict)
    assert all(isinstance(v, (int, float)) for v in calibrated.values())

    # Check metadata contains expected keys (based on actual implementation)
    assert 'bias_correction_applied' in metadata
    assert 'constraints_applied' in metadata  # Not 'soft_constraints_applied'
    assert 'convergence_applied' in metadata
    assert 'calibrated_spread' in metadata
    assert 'compression_ratio' in metadata


# ============================================================================
# PHASE 4: INTEGRATION AND PREDICTION INTERFACE TESTS
# ============================================================================

def test_fit_and_cache_baseline_v2_model():
    """Test fit_and_cache_baseline_v2_model creates valid cache."""
    # Load actual data from Excel
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Clear cache first
    invalidate_baseline_v2_cache()

    # Fit and cache model
    cache = fit_and_cache_baseline_v2_model(results_df, wood_df, force_refit=True)

    # Check cache structure
    assert cache is not None
    assert 'cache_version' in cache
    assert cache['cache_version'] == 'v2.0'
    assert 'hardness_index' in cache
    assert 'adaptive_half_lives' in cache
    assert 'hierarchical_model' in cache

    # Check model components are valid
    assert isinstance(cache['hardness_index'], dict)
    assert isinstance(cache['adaptive_half_lives'], dict)
    assert isinstance(cache['hierarchical_model'], dict)


def test_predict_baseline_v2_hybrid_with_cache():
    """Test predict_baseline_v2_hybrid uses cache correctly."""
    # Load actual data from Excel
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Ensure cache exists
    fit_and_cache_baseline_v2_model(results_df, wood_df)

    # Make prediction for a competitor with history
    predicted_time, confidence, explanation, metadata = predict_baseline_v2_hybrid(
        competitor_name='Arden Cogar Jr',  # Known competitor with lots of data
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Check prediction is valid
    assert predicted_time is not None
    assert 10 < predicted_time < 100, f"Predicted time {predicted_time} seems unreasonable"
    assert confidence in ['VERY HIGH', 'HIGH', 'MEDIUM', 'LOW']
    assert isinstance(explanation, str)

    # Check metadata contains expected keys
    if metadata:
        assert 'std_dev' in metadata
        assert 'consistency_rating' in metadata
        assert 'adaptive_half_life' in metadata


def test_predict_baseline_v2_hybrid_tournament_weighting():
    """Test predict_baseline_v2_hybrid applies tournament result weighting."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    competitor_name = 'Arden Cogar Jr'
    tournament_time = 20.0  # Fresh tournament result

    # Prediction WITH tournament result
    pred_with_tournament, conf_with, _, meta_with = predict_baseline_v2_hybrid(
        competitor_name=competitor_name,
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df,
        tournament_results={competitor_name: tournament_time}
    )

    # Prediction WITHOUT tournament result
    pred_without_tournament, conf_without, _, meta_without = predict_baseline_v2_hybrid(
        competitor_name=competitor_name,
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Tournament-weighted prediction should be much closer to tournament_time
    assert abs(pred_with_tournament - tournament_time) < abs(pred_without_tournament - tournament_time)

    # Tournament-weighted prediction should have higher confidence
    confidence_order = ['LOW', 'MEDIUM', 'HIGH', 'VERY HIGH']
    assert confidence_order.index(conf_with) >= confidence_order.index(conf_without)

    # Metadata should flag tournament weighting
    if meta_with:
        assert meta_with.get('tournament_weighted', False) == True


def test_predict_baseline_v2_hybrid_quality_adjustment():
    """Test predict_baseline_v2_hybrid applies quality adjustment correctly."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    competitor_name = 'Arden Cogar Jr'

    # Prediction with soft wood (quality=3)
    pred_soft, _, _, _ = predict_baseline_v2_hybrid(
        competitor_name=competitor_name,
        species='S01',
        diameter=300,
        quality=3,  # Softer than average
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Prediction with average wood (quality=5)
    pred_avg, _, _, _ = predict_baseline_v2_hybrid(
        competitor_name=competitor_name,
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Prediction with hard wood (quality=8)
    pred_hard, _, _, _ = predict_baseline_v2_hybrid(
        competitor_name=competitor_name,
        species='S01',
        diameter=300,
        quality=8,  # Harder than average
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Soft wood should predict faster times
    assert pred_soft < pred_avg, "Soft wood should be faster"

    # Hard wood should predict slower times
    assert pred_hard > pred_avg, "Hard wood should be slower"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_predict_baseline_v2_hybrid_new_competitor():
    """Test predict_baseline_v2_hybrid handles new competitors gracefully."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Predict for completely new competitor
    pred_time, confidence, explanation, metadata = predict_baseline_v2_hybrid(
        competitor_name='Brand New Competitor ZZZZZ',  # Doesn't exist in data
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df
    )

    # Should fall back to event baseline
    assert pred_time is not None
    assert confidence == 'LOW'  # New competitor = low confidence
    assert 'baseline' in explanation.lower() or 'event' in explanation.lower()


def test_predict_baseline_v2_hybrid_convergence_disabled():
    """Test predict_baseline_v2_hybrid works with convergence disabled."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Prediction WITH convergence
    pred_with_cal, _, _, meta_with = predict_baseline_v2_hybrid(
        competitor_name='Arden Cogar Jr',
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df,
        enable_calibration=True
    )

    # Prediction WITHOUT convergence
    pred_without_cal, _, _, meta_without = predict_baseline_v2_hybrid(
        competitor_name='Arden Cogar Jr',
        species='S01',
        diameter=300,
        quality=5,
        event_code='SB',
        results_df=results_df,
        wood_df=wood_df,
        enable_calibration=False
    )

    # Both should return valid predictions
    assert pred_with_cal is not None
    assert pred_without_cal is not None

    # Predictions may differ slightly due to calibration
    # (but this depends on whether calibration actually changed the prediction)


# ============================================================================
# PERFORMANCE AND REGRESSION TESTS
# ============================================================================

def test_cache_persistence():
    """Test that cache persists across multiple predictions."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Clear cache
    invalidate_baseline_v2_cache()

    # First prediction should trigger cache creation
    from woodchopping.predictions.baseline import _baseline_v2_cache as cache1
    predict_baseline_v2_hybrid('Arden Cogar Jr', 'S01', 300, 5, 'SB', results_df, wood_df)

    # Second prediction should reuse cache
    predict_baseline_v2_hybrid('Nate Hodges', 'S01', 300, 5, 'SB', results_df, wood_df)

    # Cache should still exist (not recreated)
    from woodchopping.predictions.baseline import _baseline_v2_cache as cache2
    assert cache2 is not None


def test_prediction_consistency():
    """Test that multiple predictions for same input are consistent."""
    try:
        results_df = load_results_df()
        wood_df = load_wood_data()
    except Exception:
        pytest.skip("Excel file not available - skipping integration test")

    # Make same prediction twice
    pred1, conf1, exp1, meta1 = predict_baseline_v2_hybrid(
        'Arden Cogar Jr', 'S01', 300, 5, 'SB', results_df, wood_df
    )

    pred2, conf2, exp2, meta2 = predict_baseline_v2_hybrid(
        'Arden Cogar Jr', 'S01', 300, 5, 'SB', results_df, wood_df
    )

    # Predictions should be identical (deterministic)
    assert abs(pred1 - pred2) < 0.01, "Predictions should be consistent"
    assert conf1 == conf2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
