"""
Test the "Check My Work" handicap validation feature.
"""

from woodchopping.predictions.check_my_work import check_my_work, display_check_my_work

# Create mock handicap results for testing
mock_handicap_results = [
    {
        'name': 'John Smith',
        'mark': 15,
        'predicted_time': 35.0,
        'method_used': 'ML',
        'confidence': 'HIGH',
        'predictions': {
            'baseline': {'time': 36.0, 'scaled': False},
            'ml': {'time': 35.0},
            'llm': {'time': 35.5}
        }
    },
    {
        'name': 'Jane Doe',
        'mark': 20,
        'predicted_time': 30.0,
        'method_used': 'Baseline (scaled)',
        'confidence': 'MEDIUM',
        'predictions': {
            'baseline': {'time': 30.0, 'scaled': True, 'scaling_warning': 'Scaling: 300mm to 275mm'},
            'ml': {'time': None},
            'llm': {'time': 31.0}
        }
    },
    {
        'name': 'Bob Johnson',
        'mark': 25,
        'predicted_time': 25.0,
        'method_used': 'Baseline',
        'confidence': 'LOW',
        'predictions': {
            'baseline': {'time': 25.0, 'scaled': False, 'explanation': 'Limited history (2 results)'},
            'ml': {'time': None},
            'llm': {'time': None}
        }
    },
    {
        'name': 'Alice Williams',
        'mark': 10,
        'predicted_time': 40.0,
        'method_used': 'ML',
        'confidence': 'HIGH',
        'predictions': {
            'baseline': {'time': 52.0, 'scaled': False},  # Large discrepancy!
            'ml': {'time': 40.0},
            'llm': {'time': 41.0}
        }
    },
]

mock_wood_selection = {
    'species': 'S01',
    'size_mm': 275,
    'quality': 5,
    'event': 'UH'
}

print("="*70)
print("TEST: Check My Work Feature")
print("="*70)

# Test the check_my_work function
print("\n1. Testing check_my_work() function...")
validation = check_my_work(mock_handicap_results, mock_wood_selection)

print(f"\nStatus: {validation['status']}")
print(f"Recommendation: {validation['recommendation']}")
print(f"\nCritical Issues: {len(validation['critical_issues'])}")
for issue in validation['critical_issues']:
    print(f"  - {issue}")

print(f"\nWarnings: {len(validation['warnings'])}")
for warning in validation['warnings']:
    print(f"  - {warning}")

print(f"\nInfo: {len(validation['info'])}")
for info_item in validation['info']:
    print(f"  - {info_item}")

print(f"\nDetails:")
print(f"  Large discrepancies: {len(validation['details']['large_discrepancies'])}")
print(f"  Low confidence: {len(validation['details']['low_confidence'])}")
print(f"  Scaled predictions: {len(validation['details']['scaled_predictions'])}")
print(f"  Finish spread: {validation['details']['finish_spread']:.2f}s")

# Test the display function
print("\n" + "="*70)
print("2. Testing display_check_my_work() function...")
print("="*70)

display_check_my_work(mock_handicap_results, mock_wood_selection)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
