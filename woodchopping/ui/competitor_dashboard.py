"""
Ultimate Competitor Dashboard (A9 + B2 + B4)

Comprehensive competitor performance dashboard integrating:
- B2: Historical performance analysis
- B4: Competitor performance profiling

Accessible from Personnel Management menu only.
"""

import os
import sys

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from woodchopping.analytics.competitor_profiling import profile_competitor_strengths
from woodchopping.analytics.performance_history import analyze_performance_history
from woodchopping.data.excel_io import load_competitors_df, load_results_df


def display_competitor_dashboard():
    """
    Main entry point for the competitor dashboard.

    Prompts user to select a competitor, then displays comprehensive dashboard
    with 3 sections:
    1. Career Summary
    2. Performance Statistics (B2)
    3. Specialization Analysis (B4)
    """
    # Load competitor data
    competitors_df = load_competitors_df()

    if competitors_df.empty:
        print("\n[WARN] No competitors found in roster.")
        print("Please add competitors first (Option 4 -> Add Competitor).\n")
        input("Press Enter to return to menu...")
        return

    # Display competitor selection menu
    print("\n" + "=" * 70)
    print("COMPETITOR DASHBOARD - SELECT COMPETITOR".center(70))
    print("=" * 70)
    print("\nAvailable Competitors:")
    print("-" * 70)

    competitors_list = competitors_df["competitor_name"].tolist()
    for idx, name in enumerate(competitors_list, 1):
        print(f"  {idx}. {name}")

    print("-" * 70)

    # Get user selection
    while True:
        try:
            choice = input("\nEnter competitor number (or 'q' to quit): ").strip().lower()

            if choice == "q":
                return

            choice_num = int(choice)
            if 1 <= choice_num <= len(competitors_list):
                selected_competitor = competitors_list[choice_num - 1]
                break
            else:
                print(f"Please enter a number between 1 and {len(competitors_list)}.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")

    # Load and prepare results data
    results_df = _load_and_prepare_results()

    if results_df.empty:
        print("\n[WARN] No historical results found for analysis.")
        print("Please add competition results first.\n")
        input("Press Enter to return to menu...")
        return

    # Get competitor info
    comp_info = competitors_df[competitors_df["competitor_name"] == selected_competitor].iloc[0]

    # Generate dashboard
    _generate_dashboard(selected_competitor, comp_info, results_df)


def _load_and_prepare_results() -> pd.DataFrame:
    """
    Load results and rename columns to match analytics module expectations.

    Returns:
        DataFrame with columns: Competitor, Event, Time (seconds), Size (mm), Species Code, Date
    """
    results_df = load_results_df()

    if results_df.empty:
        return pd.DataFrame()

    # Rename columns to match what analytics modules expect
    column_mapping = {
        "competitor_name": "Competitor",
        "event": "Event",
        "raw_time": "Time (seconds)",
        "size_mm": "Size (mm)",
        "species": "Species Code",
        "date": "Date",
    }

    results_df = results_df.rename(columns=column_mapping)

    return results_df


def _generate_dashboard(competitor_name: str, comp_info: pd.Series, results_df: pd.DataFrame):
    """
    Generate and display the complete competitor dashboard.

    Args:
        competitor_name: Name of the competitor
        comp_info: Series with competitor info (from competitors_df)
        results_df: DataFrame with historical results
    """
    # Clear screen (platform-independent)
    os.system("cls" if os.name == "nt" else "clear")

    # Run analytics
    history_analysis = analyze_performance_history(competitor_name, results_df)
    profile_analysis = profile_competitor_strengths(competitor_name, results_df)

    # Display header
    print("╔" + "═" * 68 + "╗")
    print("║" + "COMPETITOR PERFORMANCE DASHBOARD".center(68) + "║")
    print("╠" + "═" * 68 + "╣")

    # Basic info line
    name_str = f"Name: {competitor_name}"
    country_str = f"Country: {comp_info.get('competitor_country', 'N/A')}"
    state_str = f"State: {comp_info.get('state_province', 'N/A')}"
    gender_str = f"Gender: {comp_info.get('gender', 'N/A')}"

    info_line = f"║  {name_str:<66}║"
    details_line = f"║  {country_str:<22} {state_str:<22} {gender_str:<18}║"

    print(info_line)
    print(details_line)
    print("╚" + "═" * 68 + "╝")
    print()

    # SECTION 1: Career Summary
    _display_career_summary(history_analysis)

    # SECTION 2: Performance Statistics (B2)
    _display_performance_statistics(history_analysis)

    # SECTION 3: Specialization Analysis (B4)
    _display_specialization_analysis(profile_analysis)

    # Footer
    print("\n[Press Enter to return to menu]")
    input()


def _display_career_summary(history: dict):
    """Display Section 1: Career Summary."""
    print("+" + "-" * 68 + "+")
    print("| SECTION 1: CAREER SUMMARY" + " " * 42 + "|")
    print("+" + "-" * 68 + "+")

    # Total competitions
    print(f"| Total Competitions: {history['total_comps']:<48}|")

    # Event breakdown
    if history["event_breakdown"]:
        event_str = ", ".join([f"{event} ({count})" for event, count in history["event_breakdown"].items()])
        print(f"| Events: {event_str:<58}|")
    else:
        print(f"| Events: No data{' ' * 53}|")

    # Date range
    if history["date_range"]:
        dr = history["date_range"]
        date_range_str = f"{dr['first']} to {dr['last']} (available for {dr['available']}/{dr['total']} results)"
        print(f"| Date Range: {date_range_str:<56}|")
        print(f"| First Competition: {dr['first_ago']:<50}|")
        print(f"| Last Competition: {dr['last_ago']:<51}|")
    else:
        print(f"| Date Range: Date information not available{' ' * 26}|")

    print("+" + "-" * 68 + "+")
    print()


def _display_performance_statistics(history: dict):
    """Display Section 2: Performance Statistics (B2 Integration)."""
    print("+" + "-" * 68 + "+")
    print("| SECTION 2: PERFORMANCE STATISTICS (B2 Integration)" + " " * 17 + "|")
    print("+" + "-" * 68 + "+")

    if not history["by_event"]:
        print("| No performance data available" + " " * 38 + "|")
        print("+" + "-" * 68 + "+")
        print()
        return

    # Per-event statistics
    for event, stats in history["by_event"].items():
        print(f"| {event}:{' ' * (65 - len(event))}|")
        print(f"|   Best Time: {stats['best_time']:.1f} sec ({stats['best_context']})".ljust(67) + "|")
        print(f"|   Average Time: {stats['avg_time']:.1f} sec (across all diameters)".ljust(67) + "|")
        print(f"|   Consistency: ?{stats['std_dev']:.1f} sec std dev ({stats['consistency_rating']})".ljust(67) + "|")
        print("|" + " " * 68 + "|")

    # Recent form (if dates available)
    if history["recent_form"]:
        print("| Recent Form (last 5 results, if dates available):" + " " * 18 + "|")
        for form in history["recent_form"]:
            form_str = f"   {form['date']}: {form['time']:.1f} sec ({form['context']}) - {form['note']}"
            print(f"| {form_str}".ljust(67) + "|")
        print("|" + " " * 68 + "|")

    # Performance trend
    trend = history["trend"]
    if trend["slope"] is not None:
        trend_str = f"Performance Trend: {trend['direction']} (slope: {trend['slope']:.1f} sec/year)"
    else:
        trend_str = f"Performance Trend: {trend['direction']}"

    print(f"| {trend_str}".ljust(67) + "|")

    print("+" + "-" * 68 + "+")
    print()


def _display_specialization_analysis(profile: dict):
    """Display Section 3: Specialization Analysis (B4 Integration)."""
    print("+" + "-" * 68 + "+")
    print("| SECTION 3: SPECIALIZATION ANALYSIS (B4 Integration)" + " " * 16 + "|")
    print("+" + "-" * 68 + "+")

    # Preferred event
    print(f"| Preferred Event: {profile['preferred_event']}".ljust(67) + "|")

    # Preferred diameter
    if profile["preferred_diameter"]:
        pd_info = profile["preferred_diameter"]
        pref_diam_str = f"Preferred Diameter: {pd_info['diameter']}mm ({pd_info['reason']})"
        print(f"| {pref_diam_str}".ljust(67) + "|")
    else:
        print("| Preferred Diameter: Insufficient data (need 3+ results per diameter)".ljust(67) + "|")

    # Preferred species
    if profile["preferred_species"]:
        ps_info = profile["preferred_species"]
        pref_species_str = f"Preferred Species: {ps_info['species']} ({ps_info['reason']})"
        print(f"| {pref_species_str}".ljust(67) + "|")
    else:
        print("| Preferred Species: Insufficient data (need 3+ results per species)".ljust(67) + "|")

    print("|" + " " * 68 + "|")

    # Diameter breakdown
    if profile["diameter_breakdown"]:
        print("| Diameter Performance Breakdown:" + " " * 37 + "|")
        for diameter in sorted(profile["diameter_breakdown"].keys()):
            stats = profile["diameter_breakdown"][diameter]
            rating_flag = " ?" if stats["rating"] == "STRONGEST" else ""
            diam_str = f"   {diameter}mm: {stats['avg_time']:.1f} sec avg ({stats['count']} results) - {stats['rating']}{rating_flag}"
            print(f"| {diam_str}".ljust(67) + "|")
        print("|" + " " * 68 + "|")
    else:
        print("| Diameter Performance Breakdown: No data" + " " * 28 + "|")
        print("|" + " " * 68 + "|")

    # Species breakdown (only species with 3+ results)
    if profile["species_breakdown"]:
        species_with_data = {k: v for k, v in profile["species_breakdown"].items() if v["count"] >= 3}

        if species_with_data:
            print("| Species Performance Breakdown (only species with 3+ results):" + " " * 6 + "|")
            for species in sorted(species_with_data.keys()):
                stats = species_with_data[species]
                rating_flag = " ?" if stats["rating"] == "STRONGEST" else ""
                species_str = f"   {species}: {stats['avg_time']:.1f} sec avg ({stats['count']} results) - {stats['rating']}{rating_flag}"
                print(f"| {species_str}".ljust(67) + "|")
            print("|" + " " * 68 + "|")
        else:
            print("| Species Performance Breakdown: Insufficient data (need 3+ results)" + " " * 1 + "|")
            print("|" + " " * 68 + "|")

    # Outlier detection
    fast_outliers = profile["outliers"]["fast"]
    slow_outliers = profile["outliers"]["slow"]

    if fast_outliers or slow_outliers:
        print("| Outlier Detection:" + " " * 50 + "|")

        if fast_outliers:
            for outlier in fast_outliers[:3]:  # Show top 3
                outlier_str = f"   Unusually Fast: {outlier['time']:.1f} sec ({outlier['context']}) - {outlier['z_score']:.1f} std dev"
                print(f"| {outlier_str}".ljust(67) + "|")

        if slow_outliers:
            for outlier in slow_outliers[:3]:  # Show top 3
                outlier_str = f"   Unusually Slow: {outlier['time']:.1f} sec ({outlier['context']}) - {outlier['z_score']:.1f} std dev"
                print(f"| {outlier_str}".ljust(67) + "|")
    else:
        print("| Outlier Detection: No significant outliers detected" + " " * 16 + "|")

    print("+" + "-" * 68 + "+")
