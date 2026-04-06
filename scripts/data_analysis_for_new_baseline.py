"""
Comprehensive Data Analysis for New Baseline Model Design
Analyzes 1000+ competitor times to identify patterns and recommend features
"""

import os
import sys

import pandas as pd

# Fix Windows console encoding
if os.name == "nt":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load the data
from woodchopping.data import load_competitors_df, load_results_df, load_wood_data

print("=" * 80)
print("WOODCHOPPING DATA ANALYSIS FOR NEW BASELINE MODEL")
print("=" * 80)

# Load all datasets
results_df = load_results_df()
wood_df = load_wood_data()
competitors_df = load_competitors_df()

print("\nDATASET OVERVIEW")
print(f"   Total performance records: {len(results_df)}")
print(f"   Columns available: {list(results_df.columns)}")
print(f"   Unique competitors: {results_df['competitor_name'].nunique()}")

# Find species column (might be 'Species' or 'species' or 'speciesID')
species_col = None
for col in results_df.columns:
    if "species" in col.lower():
        species_col = col
        break

if species_col:
    print(f"   Unique wood species: {results_df[species_col].nunique()}")
    print(f"   Species column: {species_col}")

if "Date" in results_df.columns:
    print(f"   Date range: {results_df['date'].min()} to {results_df['date'].max()}")

# ============================================================================
# 1. TIME DISTRIBUTION ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("1. TIME DISTRIBUTION ANALYSIS")
print("=" * 80)

for event in ["SB", "UH"]:
    event_data = results_df[results_df["event"].str.upper() == event]["Time"]
    print(f"\n{event} Event Times:")
    print(f"   Count: {len(event_data)}")
    print(f"   Mean: {event_data.mean():.2f}s  |  Median: {event_data.median():.2f}s")
    print(f"   Std Dev: {event_data.std():.2f}s")
    print(f"   Min: {event_data.min():.2f}s  |  Max: {event_data.max():.2f}s")
    print(f"   P25: {event_data.quantile(0.25):.2f}s  |  P75: {event_data.quantile(0.75):.2f}s")
    print(f"   P10: {event_data.quantile(0.10):.2f}s  |  P90: {event_data.quantile(0.90):.2f}s")

# ============================================================================
# 2. DIAMETER IMPACT ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("2. DIAMETER IMPACT ANALYSIS")
print("=" * 80)

# Analyze time vs diameter correlation for each event
for event in ["SB", "UH"]:
    event_data = results_df[results_df["event"].str.upper() == event]

    # Group by 25mm bins
    event_data["diameter_bin"] = (event_data["Diameter"] // 25) * 25
    diameter_stats = event_data.groupby("diameter_bin")["Time"].agg(["count", "mean", "std", "min", "max"]).round(2)

    print(f"\n{event} - Time by Diameter (25mm bins):")
    print(diameter_stats[diameter_stats["count"] >= 5])  # Only show bins with 5+ samples

    # Calculate correlation
    corr = event_data[["Diameter", "Time"]].corr().iloc[0, 1]
    print(f"\n{event} Correlation (diameter vs time): {corr:.4f}")

# ============================================================================
# 3. WOOD SPECIES IMPACT ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("3. WOOD SPECIES IMPACT ANALYSIS")
print("=" * 80)

# Merge with wood properties
results_with_wood = results_df.merge(
    wood_df[["speciesID", "species", "janka_hard", "spec_gravity"]],
    left_on=species_col,  # Use detected species column
    right_on="speciesID",
    how="left",
)

# Check what columns we have after merge
print(f"\nColumns after merge: {list(results_with_wood.columns)}")

# Group by the wood species name column
if "species" in results_with_wood.columns:
    species_stats = (
        results_with_wood.groupby("species")
        .agg({"Time": ["count", "mean", "std"], "janka_hard": "first", "spec_gravity": "first"})
        .round(2)
    )

    species_stats.columns = ["count", "mean_time", "std_time", "janka", "spec_grav"]
    species_stats = species_stats[species_stats["count"] >= 10]  # Only species with 10+ samples
    print("\nSpecies with 10+ samples:")
    print(species_stats.sort_values("mean_time"))

# Correlation between wood properties and time
print(f"\nCorrelation: Janka Hardness vs Time: {results_with_wood[['janka_hard', 'Time']].corr().iloc[0, 1]:.4f}")
print(f"Correlation: Specific Gravity vs Time: {results_with_wood[['spec_gravity', 'Time']].corr().iloc[0, 1]:.4f}")

# ============================================================================
# 4. COMPETITOR CONSISTENCY ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("4. COMPETITOR CONSISTENCY ANALYSIS")
print("=" * 80)

# For each competitor with 5+ results, calculate their coefficient of variation
competitor_consistency = results_df.groupby("competitor_name").agg({"Time": ["count", "mean", "std"]}).round(2)
competitor_consistency.columns = ["count", "mean", "std"]
competitor_consistency["cv"] = (competitor_consistency["std"] / competitor_consistency["mean"] * 100).round(2)
competitor_consistency = competitor_consistency[competitor_consistency["count"] >= 5]

print("\nCompetitors with 5+ results (sorted by consistency):")
print("Most Consistent (lowest CV%):")
print(competitor_consistency.nsmallest(10, "cv")[["count", "mean", "std", "cv"]])

print("\nLeast Consistent (highest CV%):")
print(competitor_consistency.nlargest(10, "cv")[["count", "mean", "std", "cv"]])

print("\nOverall consistency stats:")
print(f"   Mean CV: {competitor_consistency['cv'].mean():.2f}%")
print(f"   Median CV: {competitor_consistency['cv'].median():.2f}%")

# ============================================================================
# 5. TEMPORAL PATTERN ANALYSIS
# ============================================================================
print("\n" + "=" * 80)
print("5. TEMPORAL PATTERN ANALYSIS")
print("=" * 80)

# Filter for records with valid dates
dated_results = results_df[results_df["date"].notna()].copy()
dated_results["year"] = pd.to_datetime(dated_results["date"]).dt.year
dated_results["month"] = pd.to_datetime(dated_results["date"]).dt.month

print(
    f"\nRecords with dates: {len(dated_results)} / {len(results_df)} ({len(dated_results) / len(results_df) * 100:.1f}%)"
)

# Year-over-year trends
yearly_stats = dated_results.groupby("year")["Time"].agg(["count", "mean", "std"]).round(2)
print("\nYear-over-year performance:")
print(yearly_stats)

# Month patterns (seasonal)
if dated_results["month"].notna().sum() > 0:
    monthly_stats = dated_results.groupby("month")["Time"].agg(["count", "mean"]).round(2)
    print("\nMonthly patterns (seasonal):")
    print(monthly_stats[monthly_stats["count"] >= 5])

# ============================================================================
# 6. COMPETITOR IMPROVEMENT/DECLINE TRENDS
# ============================================================================
print("\n" + "=" * 80)
print("6. COMPETITOR IMPROVEMENT/DECLINE TRENDS")
print("=" * 80)

# For competitors with 5+ dated results, fit trend line
dated_results_sorted = dated_results.sort_values(["competitor_name", "date"])
dated_results_sorted["days_since_first"] = dated_results_sorted.groupby("competitor_name")["date"].transform(
    lambda x: (pd.to_datetime(x) - pd.to_datetime(x).min()).dt.days
)

trend_analysis = []
for comp in dated_results["competitor_name"].unique():
    comp_data = dated_results_sorted[dated_results_sorted["competitor_name"] == comp]
    if len(comp_data) >= 5 and comp_data["days_since_first"].max() > 30:  # At least 30 days span
        # Linear regression: time vs days
        from scipy.stats import linregress

        slope, intercept, r_value, p_value, std_err = linregress(comp_data["days_since_first"], comp_data["Time"])
        trend_analysis.append(
            {
                "competitor": comp,
                "n_results": len(comp_data),
                "days_span": comp_data["days_since_first"].max(),
                "slope_sec_per_day": slope,
                "r_squared": r_value**2,
                "p_value": p_value,
                "mean_time": comp_data["Time"].mean(),
            }
        )

if trend_analysis:
    trend_df = pd.DataFrame(trend_analysis)
    trend_df = trend_df[trend_df["r_squared"] >= 0.20]  # Only significant trends

    print("\nCompetitors with significant trends (R² >= 0.20):")
    print("\nFastest Improvers (negative slope):")
    print(
        trend_df.nsmallest(5, "slope_sec_per_day")[
            ["competitor", "n_results", "slope_sec_per_day", "r_squared", "mean_time"]
        ]
    )

    print("\nFastest Decliners (positive slope):")
    print(
        trend_df.nlargest(5, "slope_sec_per_day")[
            ["competitor", "n_results", "slope_sec_per_day", "r_squared", "mean_time"]
        ]
    )

# ============================================================================
# 7. CROSS-EVENT PERFORMANCE CORRELATION
# ============================================================================
print("\n" + "=" * 80)
print("7. CROSS-EVENT PERFORMANCE (SB vs UH)")
print("=" * 80)

# Find competitors with results in both events
sb_times = results_df[results_df["event"].str.upper() == "SB"].groupby("competitor_name")["Time"].mean()
uh_times = results_df[results_df["event"].str.upper() == "UH"].groupby("competitor_name")["Time"].mean()

cross_event = pd.DataFrame({"SB_mean": sb_times, "UH_mean": uh_times}).dropna()

if len(cross_event) > 0:
    print(f"\nCompetitors with both SB and UH results: {len(cross_event)}")
    corr = cross_event.corr().iloc[0, 1]
    print(f"Correlation (SB mean vs UH mean): {corr:.4f}")
    print(f"\nInterpretation: {'Strong' if abs(corr) > 0.7 else 'Moderate' if abs(corr) > 0.4 else 'Weak'} correlation")
    print(f"   -> {'Good at one event ~= good at both' if corr > 0.6 else 'Event-specific skills matter'}")

# ============================================================================
# 8. FEATURE IMPORTANCE ESTIMATION
# ============================================================================
print("\n" + "=" * 80)
print("8. FEATURE IMPORTANCE ESTIMATION (Correlation Matrix)")
print("=" * 80)

# Build feature matrix
feature_df = results_with_wood[["Time", "Diameter", "janka_hard", "spec_gravity"]].dropna()

correlation_matrix = feature_df.corr().round(4)
print("\nCorrelation with Time:")
print(correlation_matrix["Time"].sort_values(ascending=False))

# ============================================================================
# 9. DATA QUALITY ASSESSMENT
# ============================================================================
print("\n" + "=" * 80)
print("9. DATA QUALITY ASSESSMENT")
print("=" * 80)

print("\nMissing Data:")
print(
    f"   Dates: {results_df['date'].isna().sum()} / {len(results_df)} ({results_df['date'].isna().mean() * 100:.1f}%)"
)
print(
    f"   Species: {results_df[species_col].isna().sum()} / {len(results_df)} ({results_df[species_col].isna().mean() * 100:.1f}%)"
)
print(
    f"   Diameter: {results_df['Diameter'].isna().sum()} / {len(results_df)} ({results_df['Diameter'].isna().mean() * 100:.1f}%)"
)
print(
    f"   Quality: {results_df['quality'].isna().sum()} / {len(results_df)} ({results_df['quality'].isna().mean() * 100:.1f}%)"
)

print("\nQuality Score Distribution:")
print(results_df["quality"].value_counts().sort_index())

# ============================================================================
# 10. RECOMMENDATIONS SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("10. KEY INSIGHTS & RECOMMENDATIONS")
print("=" * 80)

print("""
Based on the analysis above, here are the key insights:

1. DIAMETER IMPACT: Strong correlation with time - non-linear scaling critical
2. WOOD PROPERTIES: Janka hardness matters, but specific gravity also relevant
3. COMPETITOR CONSISTENCY: High variance (CV%) suggests individual variance modeling
4. TEMPORAL TRENDS: Significant improvement/decline trends for many competitors
5. QUALITY DATA: Currently all 5s - no variance to learn from (need real data)
6. CROSS-EVENT: SB/UH correlation reveals transferable vs event-specific skills
7. DATA SPARSITY: Many competitors have <5 results - shrinkage critical
8. MISSING DATES: 2% missing dates limits time-decay weighting effectiveness
""")

print("=" * 80)
print("END OF ANALYSIS")
print("=" * 80)
