"""
Championship race simulator - fun predictive tool for race outcome analysis.

This module provides a standalone championship event simulator that uses the existing
prediction and Monte Carlo simulation systems to predict race outcomes without
calculating handicap marks. All competitors start together (Mark 3) in championship
format - fastest raw time wins.

Key Features:
    - Reuses existing prediction engine (baseline, ML, LLM)
    - Runs 2 million Monte Carlo simulations for statistical confidence
    - Displays individual competitor statistics (time variations, consistency)
    - AI-powered race analysis focusing on matchups and competitive dynamics
    - View-only (no tournament state changes or Excel writes)
"""

import math
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from woodchopping.data import load_results_df
from woodchopping.predictions.baseline import get_competitor_historical_times_normalized
from woodchopping.predictions.prediction_aggregator import (
    get_all_predictions,
    select_best_prediction,
)
from woodchopping.simulation.monte_carlo import run_monte_carlo_simulation
from woodchopping.simulation.visualization import (
    generate_simulation_summary,
    visualize_simulation_results,
)
from woodchopping.ui.competitor_ui import select_all_event_competitors
from woodchopping.ui.wood_ui import select_event_code, wood_menu


def run_championship_simulator(comp_df):
    """
    Interactive championship race simulator.

    Provides a complete workflow for simulating championship-format races where
    all competitors start together (Mark 3) and fastest time wins. Uses AI-enhanced
    predictions and Monte Carlo simulation to predict race outcomes, win probabilities,
    and competitive dynamics.

    Workflow:
        1. Wood configuration (species, diameter, quality)
        2. Event type selection (SB/UH)
        3. Competitor selection (no enforced limits for fun scenarios)
        4. Optional per-competitor wood overrides
        5. Optional era normalization (time adjustments by year)
        6. Optional peak/prime form filtering for selected competitors
        7. Generate predictions for all competitors (all receive Mark 3)
        8. Run Monte Carlo simulation (2 million races)
        9. Display championship results table with win rates
        10. Display visualization (bar chart)
        11. Display individual competitor statistics
        12. AI race outcome analysis

    Args:
        comp_df: Competitor master roster DataFrame

    Returns:
        None (view-only feature, no state changes)

    Example:
        >>> from woodchopping.data import load_competitor_df
        >>> comp_df = load_competitor_df()
        >>> run_championship_simulator(comp_df)
        # User interacts with prompts to configure race and view predictions
    """
    print("\n" + "=" * 70)
    print("  CHAMPIONSHIP RACE SIMULATOR")
    print("  Predict race outcomes without handicaps - all start together!")
    print("=" * 70)

    # Initialize wood selection
    wood_selection = {"species": None, "size_mm": None, "quality": None, "event": None}

    # Step 1: Configure wood characteristics
    print("\n[STEP 1/7] Configure Wood Characteristics")
    wood_selection = wood_menu(wood_selection)

    # Step 2: Select event type (SB/UH)
    print("\n[STEP 2/7] Select Event Type")
    wood_selection = select_event_code(wood_selection)

    if not wood_selection.get("event"):
        print("\n[ERROR] Event type is required. Returning to menu.")
        input("\nPress Enter to continue...")
        return

    # Step 3: Select competitors
    print("\n[STEP 3/7] Select Competitors")
    print("Note: Championship simulator supports 2-8 competitors.")
    while True:
        from woodchopping.data import load_results_df

        results_df = load_results_df()
        selected_df = select_all_event_competitors(
            comp_df,
            max_competitors=8,
            results_df=results_df,
            event_code=wood_selection.get("event"),
            wood_info=wood_selection,
        )

        if selected_df.empty:
            print("\n[ERROR] No competitors selected. Returning to menu.")
            input("\nPress Enter to continue...")
            return

        if len(selected_df) < 2:
            print("\n[ERROR] Minimum 2 competitors required for simulation.")
            continue

        if len(selected_df) > 8:
            print("\n[ERROR] Maximum 8 competitors allowed for this simulator.")
            continue

        break

    # Step 4: Custom wood per competitor (optional)
    print("\n[STEP 4/7] Customize Wood per Competitor")
    competitor_woods = _configure_competitor_woods(selected_df, wood_selection)
    if competitor_woods is None:
        print("\nReturning to menu...")
        return

    results_df = load_results_df()

    # Step 5: Era normalization (optional)
    print("\n[STEP 5/7] Era Normalization")
    era_options = _select_era_normalization(results_df)
    if era_options.get("enabled"):
        results_df = _apply_era_normalization(
            results_df,
            anchor_year=era_options.get("anchor_year"),
            rate_pct=era_options.get("rate_pct"),
            max_years=era_options.get("max_years"),
        )

    # Step 6: Peak/prime form selection (optional)
    print("\n[STEP 6/7] Peak/Prime Form Options")
    peak_options = _select_peak_form(selected_df)
    peak_windows = {}
    peak_names = set()
    if peak_options.get("mode") != "none":
        peak_names = set(peak_options.get("names", []))
        peak_windows = _compute_peak_windows(
            results_df,
            selected_df,
            competitor_woods,
            peak_names,
            window_months=peak_options.get("window_months", 24),
            min_results=peak_options.get("min_results", 4),
        )
        _display_peak_windows(peak_windows, peak_names, peak_options)

    # Step 7: Generate predictions
    print("\n[STEP 7/7] Generating Predictions...")
    predictions = _generate_championship_predictions(
        selected_df,
        wood_selection,
        competitor_woods,
        results_df=results_df,
        peak_windows=peak_windows,
        peak_names=peak_names,
    )

    if not predictions:
        print("\n[ERROR] Prediction generation failed. Returning to menu.")
        input("\nPress Enter to continue...")
        return

    # Simulation output options
    sim_options = _select_sim_options(predictions)
    if sim_options.get("prediction_heatmap"):
        sim_options["prediction_table"] = True

    if sim_options.get("prediction_table"):
        _display_championship_results(
            predictions, wood_selection, show_heatmap=sim_options.get("prediction_heatmap", False)
        )

    if sim_options.get("prediction_disagreement"):
        _display_prediction_disagreement(predictions)

    if sim_options.get("confidence_weighted"):
        _display_confidence_weighted_leaderboard(predictions)

    if sim_options.get("personal_best_watch"):
        _display_personal_best_watch(predictions, wood_selection)

    if sim_options.get("cross_wood_transfer"):
        _display_cross_wood_transferability(predictions, wood_selection)

    if sim_options.get("wood_swap_sensitivity"):
        _display_wood_swap_sensitivity(
            predictions,
            selected_df,
            wood_selection,
            competitor_woods,
            results_df,
            peak_windows,
            peak_names,
        )

    # Run Monte Carlo simulation
    sim_outputs = (
        sim_options.get("monte_carlo_summary")
        or sim_options.get("visualization")
        or sim_options.get("individual_stats")
        or sim_options.get("championship_analysis")
        or sim_options.get("bracket_projection")
        or sim_options.get("bracket_simulation")
        or sim_options.get("best_of_three")
        or sim_options.get("podium_margins")
        or sim_options.get("upset_alert")
        or sim_options.get("safe_performers")
        or sim_options.get("ai_analysis")
        or sim_options.get("live_updates")
    )

    analysis = None
    if sim_outputs:
        num_simulations = 10_000_000
        print(f"\n[SIMULATION] Running {num_simulations:,} race simulations...")
        print("This may take several minutes depending on hardware.")
        analysis = run_monte_carlo_simulation(
            predictions,
            num_simulations=num_simulations,
            track_finish_orders=sim_options.get("championship_analysis", False),
            track_podium_margins=sim_options.get("podium_margins", False),
            show_live_leaders=sim_options.get("live_updates", False),
        )

    # Display simulation summary
    if sim_options.get("monte_carlo_summary") and analysis is not None:
        summary = generate_simulation_summary(analysis)
        print("\n" + summary)

    # Display visualization
    if sim_options.get("visualization") and analysis is not None:
        visualize_simulation_results(analysis)

    # Display individual competitor statistics
    if sim_options.get("individual_stats") and analysis is not None:
        _display_individual_competitor_stats(analysis, predictions)

    # Detailed championship + bracket analysis
    if sim_options.get("championship_analysis") and analysis is not None:
        _display_championship_detailed_analysis(analysis, predictions)

    if sim_options.get("podium_margins") and analysis is not None:
        _display_podium_margins(analysis)

    if sim_options.get("upset_alert") and analysis is not None:
        _display_upset_alert(analysis, predictions)

    if sim_options.get("safe_performers") and analysis is not None:
        _display_safe_performers(analysis, predictions)

    if sim_options.get("bracket_projection") and analysis is not None:
        _display_bracket_projection(analysis, predictions)

    if sim_options.get("bracket_simulation") and analysis is not None:
        _run_bracket_simulation(analysis, predictions, sim_options)

    if sim_options.get("best_of_three") and analysis is not None:
        _run_best_of_three_series(analysis, predictions, sim_options)

    # AI race analysis
    if sim_options.get("ai_analysis") and analysis is not None:
        _display_race_analysis(analysis, predictions)

    print("\n" + "=" * 70)
    print("  CHAMPIONSHIP SIMULATOR COMPLETE")
    print("=" * 70)
    input("\nPress Enter to return to main menu...")


def _generate_championship_predictions(
    selected_df,
    wood_selection: Dict,
    competitor_woods: Dict[str, Dict],
    results_df: Optional[pd.DataFrame] = None,
    peak_windows: Optional[Dict[str, Dict]] = None,
    peak_names: Optional[set] = None,
) -> List[Dict]:
    """
    Generate predictions for all competitors with Mark 3 (championship format).

    Uses the standard prediction pipeline (baseline, ML, LLM) but assigns
    Mark 3 to all competitors since championship format has no handicaps.

    Args:
        selected_df: DataFrame of selected competitors
        wood_selection: Wood characteristics dict

    Returns:
        List of prediction dicts sorted by predicted time (fastest first)
    """
    if results_df is None:
        results_df = load_results_df()
    predictions = []

    total = len(selected_df)
    print(f"\nGenerating predictions for {total} competitors...")

    for idx, (_, row) in enumerate(selected_df.iterrows(), 1):
        comp_name = row["competitor_name"]
        comp_wood = competitor_woods.get(comp_name, wood_selection)
        prime_info = None
        results_for_comp = results_df
        if peak_names and peak_windows:
            if comp_name in peak_names:
                prime_info = peak_windows.get(comp_name)
                if prime_info and prime_info.get("status") == "peak":
                    results_for_comp = _apply_peak_window(
                        results_df,
                        comp_name,
                        prime_info.get("start_date"),
                        prime_info.get("end_date"),
                    )

        # Progress indicator
        sys.stdout.write(f"\r  Progress: {idx}/{total} ({comp_name[:30]}...)")
        sys.stdout.flush()

        # Get all 3 prediction methods
        all_preds = get_all_predictions(
            comp_name,
            comp_wood["species"],
            comp_wood["size_mm"],
            comp_wood["quality"],
            comp_wood["event"],
            results_for_comp,
            tournament_results=None,  # No tournament weighting for mock events
        )

        # Select best prediction
        pred_time, method, confidence, explanation = select_best_prediction(all_preds)

        predictions.append(
            {
                "name": comp_name,
                "predicted_time": pred_time,
                "mark": 3,  # Championship: everyone starts together
                "method_used": method,
                "confidence": confidence,
                "predictions": all_preds,
                "wood": dict(comp_wood),
                "prime_window": prime_info,
            }
        )

    print("\n")  # New line after progress

    # Sort by predicted time (fastest first for championship)
    predictions.sort(key=lambda x: x["predicted_time"])

    return predictions


def _display_championship_results(predictions: List[Dict], wood_selection: Dict, show_heatmap: bool = False):
    """
    Display championship race predictions in table format.

    Shows predicted times and prediction methods before Monte Carlo simulation.
    After simulation, win rates and podium percentages will be shown.

    Args:
        predictions: List of prediction dicts
        wood_selection: Wood characteristics for header display
    """
    from woodchopping.data import get_species_name_from_code

    species_name = get_species_name_from_code(wood_selection["species"])

    any_custom = any(pred.get("wood") and pred["wood"] != wood_selection for pred in predictions)
    line_width = 96 if any_custom else 80

    print("\n" + "=" * line_width)
    print("  CHAMPIONSHIP RACE PREDICTIONS")
    print("=" * line_width)
    print(f"\nWood: {species_name}, {wood_selection['size_mm']}mm, Quality {wood_selection['quality']}")
    print(f"Event: {wood_selection['event']}")
    print(f"Competitors: {len(predictions)}")
    if any_custom:
        print("Note: Custom wood overrides applied for some competitors.")
    any_prime = any(pred.get("prime_window", {}).get("status") == "peak" for pred in predictions)
    if any_prime:
        print("Note: Peak/prime windows applied for selected competitors.")

    print("\n" + "-" * line_width)
    if any_custom:
        if show_heatmap:
            print(f"{'#':<4} {'Competitor':<22} {'Pred. Time':<12} {'Method':<8} {'Conf':<6} {'Heat':<4} {'Wood':<18}")
        else:
            print(f"{'#':<4} {'Competitor':<24} {'Pred. Time':<12} {'Method':<8} {'Conf':<6} {'Wood':<18}")
    else:
        if show_heatmap:
            print(f"{'#':<4} {'Competitor':<26} {'Pred. Time':<12} {'Method':<8} {'Conf':<6} {'Heat':<4}")
        else:
            print(f"{'#':<4} {'Competitor':<28} {'Pred. Time':<12} {'Method':<8} {'Conf':<6}")
    print("-" * line_width)

    for idx, pred in enumerate(predictions, 1):
        heat = _confidence_symbol(pred["confidence"]) if show_heatmap else ""
        if any_custom:
            wood = pred.get("wood", wood_selection)
            size_val = wood.get("size_mm")
            size_label = f"{size_val:.0f}" if isinstance(size_val, (int, float)) else "?"
            wood_label = f"{wood.get('species', '?')}/{size_label}/Q{wood.get('quality', '?')}"
            if show_heatmap:
                print(
                    f"{idx:<4} {pred['name']:<22} {pred['predicted_time']:>6.1f}s      "
                    f"{pred['method_used']:<8} {pred['confidence']:<6} {heat:<4} {wood_label:<18}"
                )
            else:
                print(
                    f"{idx:<4} {pred['name']:<24} {pred['predicted_time']:>6.1f}s      "
                    f"{pred['method_used']:<8} {pred['confidence']:<6} {wood_label:<18}"
                )
        else:
            if show_heatmap:
                print(
                    f"{idx:<4} {pred['name']:<26} {pred['predicted_time']:>6.1f}s      "
                    f"{pred['method_used']:<8} {pred['confidence']:<6} {heat:<4}"
                )
            else:
                print(
                    f"{idx:<4} {pred['name']:<28} {pred['predicted_time']:>6.1f}s      "
                    f"{pred['method_used']:<8} {pred['confidence']:<6}"
                )

    print("-" * line_width)
    print("\nNote: All competitors start together (Mark 3) - fastest time wins!")


def _select_era_normalization(results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Prompt for optional era normalization (adjust times to a reference year).
    """
    options = {"enabled": False, "anchor_year": None, "rate_pct": 0.2, "max_years": 30}

    if results_df is None or results_df.empty or "date" not in results_df.columns:
        print("No dated results available. Era normalization disabled.")
        return options

    dated = results_df["date"].dropna()
    if dated.empty:
        print("No dated results available. Era normalization disabled.")
        return options

    enable = input("Enable era normalization? (y/n): ").strip().lower()
    if enable != "y":
        return options

    options["enabled"] = True
    default_anchor = int(pd.to_datetime(dated).dt.year.max()) if not dated.empty else datetime.now().year
    anchor_str = input(f"Reference year (default {default_anchor}): ").strip()
    if anchor_str:
        try:
            options["anchor_year"] = int(anchor_str)
        except ValueError:
            print("Invalid year. Using default.")
            options["anchor_year"] = default_anchor
    else:
        options["anchor_year"] = default_anchor

    rate_str = input("Improvement rate per year in % (default 0.2): ").strip()
    if rate_str:
        try:
            options["rate_pct"] = float(rate_str)
        except ValueError:
            print("Invalid rate. Using default 0.2%.")

    max_str = input("Max year adjustment (cap, default 30): ").strip()
    if max_str:
        try:
            options["max_years"] = int(max_str)
        except ValueError:
            print("Invalid cap. Using default 30 years.")

    return options


def _apply_era_normalization(
    results_df: pd.DataFrame, anchor_year: int, rate_pct: float, max_years: int
) -> pd.DataFrame:
    """
    Adjust raw_time to a reference year using a linear improvement rate.
    """
    if results_df is None or results_df.empty:
        return results_df

    df = results_df.copy()
    if "date" not in df.columns or "raw_time" not in df.columns:
        return df

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    date_mask = df["date"].notna()
    if not date_mask.any():
        return df

    years = df.loc[date_mask, "date"].dt.year.astype(int)
    year_diff = (years - int(anchor_year)).clip(lower=-max_years, upper=max_years)
    rate = float(rate_pct) / 100.0
    factor = 1.0 + (year_diff * rate)
    factor = factor.clip(lower=0.5, upper=1.5)

    df.loc[date_mask, "raw_time"] = pd.to_numeric(df.loc[date_mask, "raw_time"], errors="coerce") * factor
    df["raw_time"] = pd.to_numeric(df["raw_time"], errors="coerce")

    print(f"Era normalization applied: anchor {anchor_year}, rate {rate_pct:.3f}%/yr, cap {max_years} yrs.")
    return df


def _select_peak_form(selected_df) -> Dict[str, Any]:
    """
    Prompt for optional peak/prime form simulation.
    """
    options = {"mode": "none", "names": [], "window_months": 24, "min_results": 4}

    if selected_df is None or selected_df.empty:
        return options

    print("\nPeak/prime form uses the best rolling window of dated results.")
    print("  1) Off (use full history)")
    print("  2) Use peak form for ALL selected competitors")
    print("  3) Use peak form for SELECTED competitors")
    choice = input("Choose (1-3, Enter=1): ").strip()

    if choice in ("", "1"):
        return options

    if choice == "2":
        options["mode"] = "all"
        options["names"] = selected_df["competitor_name"].tolist()
    elif choice == "3":

        def _parse_indices(selection: str, max_index: int) -> List[int]:
            indices = set()
            for part in selection.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    start, end = part.split("-")
                    start_idx = int(start) - 1
                    end_idx = int(end) - 1
                    for i in range(start_idx, end_idx + 1):
                        if 0 <= i < max_index:
                            indices.add(i)
                else:
                    idx = int(part) - 1
                    if 0 <= idx < max_index:
                        indices.add(idx)
            return sorted(indices)

        print("\nSelect competitors for peak form:")
        for idx, row in enumerate(selected_df.itertuples(index=False), 1):
            print(f"  {idx:3d}) {row.competitor_name}")

        selection = input("\nPeak competitors (comma/range): ").strip()
        if not selection:
            return options

        try:
            indices = _parse_indices(selection, len(selected_df))
        except ValueError:
            print("Invalid selection. Peak form disabled.")
            return options

        if not indices:
            return options

        options["mode"] = "selected"
        options["names"] = [selected_df.iloc[i]["competitor_name"] for i in indices]
    else:
        print("Invalid selection. Peak form disabled.")
        return options

    months_str = input("Peak window length in months (default 24): ").strip()
    if months_str:
        try:
            months_val = int(months_str)
            options["window_months"] = max(6, min(120, months_val))
        except ValueError:
            print("Invalid months. Using default 24.")

    min_str = input("Minimum dated results required (default 4): ").strip()
    if min_str:
        try:
            min_val = int(min_str)
            options["min_results"] = max(2, min(20, min_val))
        except ValueError:
            print("Invalid minimum. Using default 4.")

    return options


def _compute_peak_windows(
    results_df: pd.DataFrame,
    selected_df,
    competitor_woods: Dict[str, Dict],
    peak_names: set,
    window_months: int = 24,
    min_results: int = 4,
) -> Dict[str, Dict]:
    windows = {}
    if results_df is None or results_df.empty or "date" not in results_df.columns:
        for name in peak_names:
            windows[name] = {"status": "no_data", "reason": "no dated results available"}
        return windows

    window_days = int(window_months * 30.5)
    window_delta = pd.Timedelta(days=window_days)

    for name in peak_names:
        wood = competitor_woods.get(name, {})
        event_code = wood.get("event")
        species = wood.get("species")
        diameter = wood.get("size_mm")

        historical, data_source, _ = get_competitor_historical_times_normalized(
            competitor_name=name,
            species=species,
            diameter=diameter,
            event_code=event_code,
            results_df=results_df,
            return_weights=True,
        )

        entries = []
        for time_val, date_val, _ in historical:
            if date_val is None or pd.isna(date_val):
                continue
            entries.append((float(time_val), pd.to_datetime(date_val)))

        if len(entries) < min_results:
            if entries:
                dates = sorted(d for _, d in entries)
                windows[name] = {
                    "status": "fallback",
                    "reason": f"only {len(entries)} dated result(s)",
                    "start_date": dates[0],
                    "end_date": dates[-1],
                    "samples": len(entries),
                    "mean_time": float(sum(t for t, _ in entries) / len(entries)),
                    "data_source": data_source,
                }
            else:
                windows[name] = {"status": "no_data", "reason": "no dated results available"}
            continue

        entries.sort(key=lambda x: x[1])
        best = None
        j = 0
        for i in range(len(entries)):
            start_date = entries[i][1]
            while j < len(entries) and entries[j][1] <= start_date + window_delta:
                j += 1
            window = entries[i:j]
            if len(window) < min_results:
                continue
            mean_time = float(sum(t for t, _ in window) / len(window))
            if (
                best is None
                or mean_time < best["mean_time"]
                or (mean_time == best["mean_time"] and len(window) > best["samples"])
            ):
                best = {
                    "status": "peak",
                    "start_date": window[0][1],
                    "end_date": window[-1][1],
                    "samples": len(window),
                    "mean_time": mean_time,
                    "data_source": data_source,
                }

        if best is None:
            dates = [d for _, d in entries]
            windows[name] = {
                "status": "fallback",
                "reason": "no window met minimum size",
                "start_date": min(dates),
                "end_date": max(dates),
                "samples": len(entries),
                "mean_time": float(sum(t for t, _ in entries) / len(entries)),
                "data_source": data_source,
            }
        else:
            windows[name] = best

    return windows


def _display_peak_windows(peak_windows: Dict[str, Dict], peak_names: set, options: Dict[str, Any]) -> None:
    if not peak_names:
        return

    print("\n" + "=" * 70)
    print("  PEAK/PRIME WINDOWS")
    print("=" * 70)
    print(f"Window: {options.get('window_months', 24)} months | Min results: {options.get('min_results', 4)}")
    print("Note: Uses dated results normalized by species/diameter (quality normalized to 5).")
    print("-" * 70)

    for name in sorted(peak_names):
        info = peak_windows.get(name)
        if not info:
            print(f"{name:24s} No data")
            continue

        status = info.get("status")
        if status == "peak":
            start = info.get("start_date").strftime("%Y-%m-%d")
            end = info.get("end_date").strftime("%Y-%m-%d")
            print(f"{name:24s} {start} to {end} | n={info.get('samples')} | avg {info.get('mean_time'):.2f}s")
        elif status == "fallback":
            start = info.get("start_date").strftime("%Y-%m-%d") if info.get("start_date") else "?"
            end = info.get("end_date").strftime("%Y-%m-%d") if info.get("end_date") else "?"
            print(f"{name:24s} Fallback ({info.get('reason')}) {start} to {end}")
        else:
            print(f"{name:24s} No peak data ({info.get('reason')})")

    print("-" * 70)


def _apply_peak_window(
    results_df: pd.DataFrame,
    competitor_name: str,
    start_date: Optional[pd.Timestamp],
    end_date: Optional[pd.Timestamp],
) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return results_df
    if "competitor_name" not in results_df.columns or "date" not in results_df.columns:
        return results_df
    if start_date is None or end_date is None:
        return results_df

    name_mask = (
        results_df["competitor_name"].astype(str).str.strip().str.lower() == str(competitor_name).strip().lower()
    )
    comp_rows = results_df[name_mask].copy()
    comp_rows = comp_rows[comp_rows["date"].notna()]
    comp_rows = comp_rows[(comp_rows["date"] >= start_date) & (comp_rows["date"] <= end_date)]
    if comp_rows.empty:
        return results_df

    return pd.concat([results_df[~name_mask], comp_rows], ignore_index=True)


def _select_wood_swap_scenarios(base_wood: Dict[str, Any]) -> List[Dict[str, Any]]:
    scenarios = []
    print("\nConfigure wood swap scenarios (press Enter to finish).")
    print("  1) Species swap")
    print("  2) Quality shift (+/-)")
    print("  3) Size shift mm (+/-)")
    print("  4) Custom override (species/size/quality)")
    print("  5) Done")

    while True:
        choice = input("Scenario type (1-5, Enter=5): ").strip()
        if choice in ("", "5"):
            break

        if choice == "1":
            species = input("Species code to use: ").strip()
            if not species:
                print("No species entered.")
                continue
            scenarios.append({"label": f"Species -> {species}", "species": species})
        elif choice == "2":
            delta_str = input("Quality shift (e.g. -2 or 2): ").strip()
            try:
                delta = int(delta_str)
            except ValueError:
                print("Invalid quality shift.")
                continue
            if delta == 0:
                print("Zero shift ignored.")
                continue
            scenarios.append({"label": f"Quality shift {delta:+d}", "quality_delta": delta})
        elif choice == "3":
            delta_str = input("Size shift mm (e.g. -10 or 10): ").strip()
            try:
                delta = float(delta_str)
            except ValueError:
                print("Invalid size shift.")
                continue
            if abs(delta) < 0.01:
                print("Zero shift ignored.")
                continue
            scenarios.append({"label": f"Size shift {delta:+.0f}mm", "size_delta": delta})
        elif choice == "4":
            species = input("Species code (Enter to keep): ").strip() or None
            size_str = input("Size mm (Enter to keep): ").strip()
            quality_str = input("Quality 1-10 (Enter to keep): ").strip()
            size_val = None
            qual_val = None
            if size_str:
                try:
                    size_val = float(size_str)
                except ValueError:
                    print("Invalid size.")
            if quality_str:
                try:
                    qual_val = int(quality_str)
                except ValueError:
                    print("Invalid quality.")
            scenarios.append(
                {
                    "label": "Custom override",
                    "species": species,
                    "size_override": size_val,
                    "quality_override": qual_val,
                }
            )
        else:
            print("Invalid selection.")

    return scenarios


def _apply_scenario_to_wood(wood: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(wood)
    if scenario.get("species"):
        updated["species"] = scenario["species"]

    if scenario.get("size_override") is not None:
        updated["size_mm"] = float(scenario["size_override"])
    elif scenario.get("size_delta"):
        base_val = updated.get("size_mm")
        if isinstance(base_val, (int, float)):
            updated["size_mm"] = max(1.0, float(base_val) + float(scenario["size_delta"]))

    if scenario.get("quality_override") is not None:
        updated["quality"] = int(scenario["quality_override"])
    elif scenario.get("quality_delta"):
        base_q = updated.get("quality")
        if isinstance(base_q, (int, float)):
            updated["quality"] = int(round(base_q + int(scenario["quality_delta"])))

    if "quality" in updated and isinstance(updated["quality"], (int, float)):
        updated["quality"] = max(1, min(10, int(round(updated["quality"]))))

    return updated


def _apply_scenario_to_competitor_woods(
    competitor_woods: Dict[str, Dict], base_wood: Dict[str, Any], scenario: Dict[str, Any]
) -> Dict[str, Dict]:
    swapped = {}
    for name, wood in competitor_woods.items():
        base = wood if wood else base_wood
        swapped[name] = _apply_scenario_to_wood(base, scenario)
    return swapped


def _display_wood_swap_sensitivity(
    base_predictions: List[Dict],
    selected_df,
    wood_selection: Dict,
    competitor_woods: Dict[str, Dict],
    results_df: pd.DataFrame,
    peak_windows: Dict[str, Dict],
    peak_names: set,
) -> None:
    scenarios = _select_wood_swap_scenarios(wood_selection)
    if not scenarios:
        print("\nNo wood swap scenarios selected.")
        return

    base_rank = {pred["name"]: i + 1 for i, pred in enumerate(base_predictions)}
    base_time = {pred["name"]: pred["predicted_time"] for pred in base_predictions}
    base_podium = [pred["name"] for pred in base_predictions[:3]]

    print("\n" + "=" * 70)
    print("  WOOD SWAP SENSITIVITY")
    print("=" * 70)
    print("Note: Uses same peak/era settings as baseline.")

    for scenario in scenarios:
        scenario_label = scenario.get("label", "Scenario")
        scenario_wood = _apply_scenario_to_wood(wood_selection, scenario)
        scenario_woods = _apply_scenario_to_competitor_woods(competitor_woods, wood_selection, scenario)

        print(f"\nScenario: {scenario_label}")
        print(
            f"Wood: {scenario_wood.get('species')}, {scenario_wood.get('size_mm')}mm, Q{scenario_wood.get('quality')}"
        )

        scenario_predictions = _generate_championship_predictions(
            selected_df,
            scenario_wood,
            scenario_woods,
            results_df=results_df,
            peak_windows=peak_windows,
            peak_names=peak_names,
        )

        scenario_rank = {pred["name"]: i + 1 for i, pred in enumerate(scenario_predictions)}
        scenario_time = {pred["name"]: pred["predicted_time"] for pred in scenario_predictions}
        scenario_podium = [pred["name"] for pred in scenario_predictions[:3]]

        def _fmt_time(val: Optional[float]) -> str:
            return f"{val:>7.2f}" if isinstance(val, (int, float)) else "   n/a"

        print("-" * 70)
        print(f"{'Competitor':<24} {'Base':>8} {'New':>8} {'?Time':>8} {'Rank':>9}")
        print("-" * 70)
        for name in scenario_rank.keys():
            base_t = base_time.get(name)
            new_t = scenario_time.get(name)
            delta = new_t - base_t if base_t is not None and new_t is not None else None
            base_r = base_rank.get(name)
            new_r = scenario_rank.get(name)
            rank_delta = new_r - base_r if base_r and new_r else None
            delta_label = f"{delta:+.2f}" if delta is not None else "  n/a"
            rank_label = f"{base_r:>2d}->{new_r:<2d} ({rank_delta:+d})" if rank_delta is not None else "n/a"
            print(f"{name:<24} {_fmt_time(base_t)} {_fmt_time(new_t)} {delta_label:>8} {rank_label:>9}")

        if base_podium != scenario_podium:
            print(f"Podium change: {' > '.join(base_podium)} -> {' > '.join(scenario_podium)}")
        else:
            print("Podium unchanged.")

        print("-" * 70)


def _display_individual_competitor_stats(analysis: Dict, predictions: List[Dict]):
    """
    Display detailed per-competitor statistics from Monte Carlo simulation.

    Shows time variations, consistency ratings, and performance ranges for each
    competitor based on 2 million simulated races.

    Args:
        analysis: Monte Carlo simulation analysis dict
        predictions: List of prediction dicts
    """
    print("\n" + "=" * 70)
    print("  INDIVIDUAL PERFORMANCE ANALYSIS")
    print(f"  (Based on {analysis['num_simulations']:,} simulations)")
    print("=" * 70)

    competitor_stats = analysis["competitor_time_stats"]
    winner_pcts = analysis["winner_percentages"]
    avg_positions = analysis["avg_finish_positions"]

    from woodchopping.data import get_species_name_from_code

    for pred in predictions:
        name = pred["name"]
        stats = competitor_stats[name]
        wood = pred.get("wood", {})
        species_name = get_species_name_from_code(wood.get("species")) if wood.get("species") else "Unknown"

        print(f"\nCompetitor: {name}")
        print("  " + "-" * 66)
        print(f"  Wood:               {species_name}, {wood.get('size_mm', '?')}mm, Quality {wood.get('quality', '?')}")
        print(f"  Predicted Time:     {pred['predicted_time']:>6.1f}s")
        print(f"  Average Sim Time:   {stats['mean']:>6.2f}s  (+/-{stats['std_dev']:.2f}s std dev)")
        print(f"  Time Range:         {stats['min']:>6.1f}s - {stats['max']:.1f}s")
        print(f"  25th Percentile:    {stats['p25']:>6.1f}s  |  75th Percentile: {stats['p75']:.1f}s")
        print(f"  Win Rate:           {winner_pcts[name]:>6.2f}%")
        print(f"  Avg Finish Pos:     {avg_positions[name]:>6.2f}")
        print(f"  Consistency Rating: {stats['consistency_rating']}")

    print("\n" + "=" * 70)


def _display_race_analysis(analysis: Dict, predictions: List[Dict]):
    """
    Display AI-generated race outcome analysis.

    Uses LLM to provide engaging commentary on race dynamics, likely winners,
    key matchups, and competitive narratives.

    Args:
        analysis: Monte Carlo simulation analysis dict
        predictions: List of prediction dicts
    """

    print("\n" + "=" * 70)


def _select_sim_options(predictions: List[Dict]) -> Dict[str, Any]:
    """
    Select simulation outputs. No defaults; user chooses what to display.
    """
    options_list = [
        ("prediction_table", "Prediction table"),
        ("prediction_heatmap", "Confidence heatmap (table symbols)"),
        ("prediction_disagreement", "Prediction disagreement report"),
        ("confidence_weighted", "Confidence-weighted leaderboard"),
        ("personal_best_watch", "Personal best watch"),
        ("cross_wood_transfer", "Cross-wood transferability"),
        ("wood_swap_sensitivity", "Wood swap sensitivity (species/quality/size)"),
        ("monte_carlo_summary", "Monte Carlo summary"),
        ("visualization", "Win-rate visualization"),
        ("individual_stats", "Individual competitor stats"),
        ("championship_analysis", "Championship analysis"),
        ("podium_margins", "Podium margins + photo-finish likelihood"),
        ("upset_alert", "Upset alert (variance overlap)"),
        ("safe_performers", "Safe performers list"),
        ("bracket_projection", "Bracket projection"),
        ("bracket_simulation", "Bracket simulation (multi-round Monte Carlo)"),
        ("best_of_three", "Best-of-3 head-to-head series"),
        ("ai_analysis", "AI race analysis"),
        ("live_updates", "Live sim clock + interim leaders"),
    ]

    print("\n" + "=" * 70)
    print("  SIMULATION OUTPUT OPTIONS")
    print("=" * 70)
    for idx, (_, label) in enumerate(options_list, 1):
        print(f"  {idx:2d}) {label}")
    print("\nSelect option numbers (comma/range).")
    print("Example: 1,3,5-8")

    selection = input("Options: ").strip()

    selected = set()
    if selection:
        try:
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = part.split("-")
                    for i in range(int(start), int(end) + 1):
                        if 1 <= i <= len(options_list):
                            selected.add(i)
                else:
                    idx = int(part)
                    if 1 <= idx <= len(options_list):
                        selected.add(idx)
        except ValueError:
            print("Invalid selection. No options selected.")

    options = {key: False for key, _ in options_list}
    for idx in selected:
        key = options_list[idx - 1][0]
        options[key] = True

    # Optional settings for multi-round sims
    options["fatigue_enabled"] = False
    options["fatigue_seconds"] = 0.2
    if options.get("bracket_simulation") or options.get("best_of_three"):
        fatigue = input("\nEnable fatigue model for multi-round sims? (y/n): ").strip().lower()
        if fatigue == "y":
            options["fatigue_enabled"] = True
            s = input("Fatigue per round in seconds (default 0.20): ").strip()
            if s:
                try:
                    val = float(s)
                    options["fatigue_seconds"] = max(0.0, min(2.0, val))
                except ValueError:
                    print("Invalid input. Using default fatigue.")

    # Best-of-3 series configuration
    options["best_of_three_pair"] = None
    options["best_of_three_runs"] = 20000
    if options.get("best_of_three"):
        print("\nSelect two competitors for head-to-head series:")
        for i, pred in enumerate(predictions, 1):
            print(f"  {i:2d}) {pred['name']}")
        pair = input("Enter two numbers (e.g., 1,3): ").strip()
        try:
            parts = [int(x.strip()) for x in pair.split(",")]
            if len(parts) == 2:
                idx_a = parts[0] - 1
                idx_b = parts[1] - 1
                if 0 <= idx_a < len(predictions) and 0 <= idx_b < len(predictions):
                    options["best_of_three_pair"] = (
                        predictions[idx_a]["name"],
                        predictions[idx_b]["name"],
                    )
        except ValueError:
            options["best_of_three_pair"] = None

        s = input("Number of series simulations (default 20000): ").strip()
        if s:
            try:
                options["best_of_three_runs"] = max(1000, int(s))
            except ValueError:
                print("Invalid input. Using default series count.")

    # Bracket simulation configuration
    options["bracket_sim_runs"] = 100000
    if options.get("bracket_simulation"):
        s = input("\nBracket simulation runs (default 100000): ").strip()
        if s:
            try:
                options["bracket_sim_runs"] = max(5000, int(s))
            except ValueError:
                print("Invalid input. Using default bracket runs.")

    return options


def _confidence_symbol(confidence: str) -> str:
    symbols = {"VERY HIGH": "+++", "HIGH": "++", "MEDIUM": "+", "LOW": "!", "VERY LOW": "!!"}
    return symbols.get(confidence, "")


def _display_prediction_disagreement(predictions: List[Dict]):
    print("\n" + "=" * 70)
    print("  PREDICTION DISAGREEMENT REPORT")
    print("=" * 70)
    print(f"{'Competitor':<26} {'Spread':<10} {'Spread %':<10} {'Methods':<14} {'Flag'}")
    print("-" * 70)

    for pred in predictions:
        name = pred["name"]
        preds = pred.get("predictions", {})
        times = []
        methods = []
        for key, label in (("baseline", "B"), ("ml", "M"), ("llm", "L")):
            val = preds.get(key, {}).get("time")
            if val is not None:
                times.append(val)
                methods.append(label)
        if len(times) < 2:
            spread = 0.0
            pct = 0.0
        else:
            spread = max(times) - min(times)
            pct = (spread / (sum(times) / len(times))) * 100.0

        flag = ""
        if spread >= 4.0 or pct >= 20.0:
            flag = "HIGH"
        elif spread >= 2.5 or pct >= 12.0:
            flag = "MED"

        method_str = "".join(methods) if methods else "N/A"
        print(f"{name:<26} {spread:>6.2f}s   {pct:>6.1f}%    {method_str:<14} {flag}")

    print("-" * 70)


def _display_confidence_weighted_leaderboard(predictions: List[Dict]):
    print("\n" + "=" * 70)
    print("  CONFIDENCE-WEIGHTED LEADERBOARD")
    print("=" * 70)

    penalty_map = {"VERY HIGH": 0.0, "HIGH": 0.5, "MEDIUM": 1.5, "LOW": 3.0, "VERY LOW": 4.5}

    rows = []
    for pred in predictions:
        penalty = penalty_map.get(pred["confidence"], 2.0)
        adjusted = pred["predicted_time"] + penalty
        rows.append((pred["name"], pred["predicted_time"], penalty, adjusted))

    rows.sort(key=lambda x: x[3])
    print(f"{'#':<4} {'Competitor':<24} {'Base':<8} {'Penalty':<8} {'Adjusted':<8}")
    print("-" * 70)
    for idx, row in enumerate(rows, 1):
        print(f"{idx:<4} {row[0]:<24} {row[1]:>6.1f}s   {row[2]:>6.1f}s   {row[3]:>6.1f}s")
    print("-" * 70)


def _display_personal_best_watch(predictions: List[Dict], wood_selection: Dict):
    from woodchopping.data import load_results_df

    results_df = load_results_df()
    if results_df is None or results_df.empty:
        print("\nNo historical results available for PB watch.")
        return

    print("\n" + "=" * 70)
    print("  PERSONAL BEST WATCH")
    print("=" * 70)

    shown = 0
    for pred in predictions:
        name = pred["name"]
        event = wood_selection.get("event")
        comp_rows = results_df[(results_df["Competitor"] == name) & (results_df["Event"] == event)]
        if comp_rows.empty:
            continue
        best_time = comp_rows["Time (seconds)"].min()
        if best_time <= 0:
            continue
        predicted = pred["predicted_time"]
        diff = predicted - best_time
        within = (predicted <= best_time * 1.03) or (diff <= 0.5)
        if within:
            print(f"{name:24s} Pred {predicted:>6.2f}s | PB {best_time:>6.2f}s | ? {diff:+.2f}s")
            shown += 1

    if shown == 0:
        print("No PB threats detected for this event.")

    print("-" * 70)


def _display_cross_wood_transferability(predictions: List[Dict], wood_selection: Dict):
    """
    Estimate whether competitors improve or decline with bigger/firm wood.

    Uses simple linear trends vs size (mm) and quality (1-10) within the event.
    Negative slope means faster times as size/quality increase.
    """
    results_df = load_results_df()
    if results_df is None or results_df.empty:
        print("\nNo historical results available for transferability analysis.")
        return

    event = wood_selection.get("event")
    if not event:
        print("\nNo event selected for transferability analysis.")
        return

    print("\n" + "=" * 70)
    print("  CROSS-WOOD TRANSFERABILITY")
    print("=" * 70)
    print("Negative slope = faster on bigger/harder wood")
    print(f"{'Competitor':<24} {'Size Trend':<16} {'Quality Trend':<18} {'Samples'}")
    print("-" * 70)

    for pred in predictions:
        name = pred["name"]
        comp_rows = results_df[(results_df["competitor_name"] == name) & (results_df["event"] == event)].copy()

        if comp_rows.empty:
            print(f"{name:<24} {'N/A':<16} {'N/A':<18} 0")
            continue

        size_rows = comp_rows[comp_rows["size_mm"].notna() & comp_rows["raw_time"].notna()]
        qual_rows = comp_rows[comp_rows["quality"].notna() & comp_rows["raw_time"].notna()]

        size_trend = "N/A"
        qual_trend = "N/A"

        if len(size_rows) >= 3:
            slope = np.polyfit(size_rows["size_mm"], size_rows["raw_time"], 1)[0]
            slope_10 = slope * 10.0
            if slope_10 <= -0.02:
                label = "BIG+"
            elif slope_10 >= 0.02:
                label = "BIG-"
            else:
                label = "NEUTRAL"
            size_trend = f"{slope_10:+.3f}s/10mm {label}"

        if len(qual_rows) >= 3:
            slope_q = np.polyfit(qual_rows["quality"], qual_rows["raw_time"], 1)[0]
            if slope_q <= -0.05:
                label_q = "HARD+"
            elif slope_q >= 0.05:
                label_q = "HARD-"
            else:
                label_q = "NEUTRAL"
            qual_trend = f"{slope_q:+.3f}s/Q {label_q}"

        samples = len(comp_rows)
        print(f"{name:<24} {size_trend:<16} {qual_trend:<18} {samples}")

    print("-" * 70)


def _display_podium_margins(analysis: Dict):
    print("\n" + "=" * 70)
    print("  PODIUM MARGINS")
    print("=" * 70)

    avg_12 = analysis.get("avg_podium_margin_12")
    avg_23 = analysis.get("avg_podium_margin_23")
    photo_pct = analysis.get("photo_finish_pct")
    threshold = analysis.get("photo_finish_threshold")

    if avg_12 is None:
        print("Not enough data to compute podium margins.")
        return

    print(f"Average 1st-2nd margin: {avg_12:.3f}s")
    if avg_23 is not None:
        print(f"Average 2nd-3rd margin: {avg_23:.3f}s")
    if photo_pct is not None and threshold is not None:
        print(f"Photo-finish likelihood (<= {threshold:.2f}s): {photo_pct:.2f}%")

    print("-" * 70)


def _display_upset_alert(analysis: Dict, predictions: List[Dict]):
    print("\n" + "=" * 70)
    print("  UPSET ALERT")
    print("=" * 70)

    winner_pcts = analysis.get("winner_percentages", {})
    stats = analysis.get("competitor_time_stats", {})
    if not winner_pcts:
        print("No winner data available.")
        return

    favorite = max(winner_pcts.items(), key=lambda x: x[1])[0]
    threats = []
    for pred in predictions:
        name = pred["name"]
        if name == favorite:
            continue
        win_prob = _win_probability_from_stats(name, favorite, stats)
        threats.append((name, win_prob))

    threats.sort(key=lambda x: x[1], reverse=True)
    top_threat = threats[0][1] if threats else 0.0

    if top_threat >= 0.35:
        level = "HIGH"
    elif top_threat >= 0.25:
        level = "MEDIUM"
    else:
        level = "LOW"

    print(f"Favorite: {favorite}")
    print(f"Upset risk: {level}")
    print("Top threats:")
    for name, prob in threats[:3]:
        print(f"  {name:24s} {prob * 100:5.1f}% head-to-head win vs favorite")

    print("-" * 70)


def _display_safe_performers(analysis: Dict, predictions: List[Dict]):
    print("\n" + "=" * 70)
    print("  SAFE PERFORMERS")
    print("=" * 70)

    stats = analysis.get("competitor_time_stats", {})
    winner_pcts = analysis.get("winner_percentages", {})
    std_values = [stats.get(p["name"], {}).get("std_dev") for p in predictions]
    std_values = [v for v in std_values if isinstance(v, (int, float))]
    if not std_values:
        print("No consistency data available.")
        return

    median_std = sorted(std_values)[len(std_values) // 2]
    threshold = min(3.0, median_std)

    safe = []
    for pred in predictions:
        name = pred["name"]
        std_dev = stats.get(name, {}).get("std_dev")
        if std_dev is None:
            continue
        if pred["confidence"] in ("VERY HIGH", "HIGH") and std_dev <= threshold:
            safe.append((name, winner_pcts.get(name, 0.0), std_dev))

    if not safe:
        print("No performers met the safety criteria.")
        return

    safe.sort(key=lambda x: x[1], reverse=True)
    for name, win_pct, std_dev in safe:
        print(f"{name:24s} Win {win_pct:6.2f}% | SD {std_dev:5.2f}s")

    print("-" * 70)


def _run_best_of_three_series(analysis: Dict, predictions: List[Dict], options: Dict):
    pair = options.get("best_of_three_pair")
    if not pair:
        print("\nBest-of-3 not run (no valid pair selected).")
        return

    name_a, name_b = pair
    stats = analysis.get("competitor_time_stats", {})
    mu_a = stats.get(name_a, {}).get("mean")
    mu_b = stats.get(name_b, {}).get("mean")
    sigma_a = stats.get(name_a, {}).get("std_dev")
    sigma_b = stats.get(name_b, {}).get("std_dev")

    if mu_a is None or mu_b is None or sigma_a is None or sigma_b is None:
        print("\nBest-of-3 not available (missing stats).")
        return

    runs = options.get("best_of_three_runs", 20000)
    fatigue_enabled = options.get("fatigue_enabled", False)
    fatigue_seconds = options.get("fatigue_seconds", 0.2)

    series_wins = {name_a: 0, name_b: 0}
    score_counts = {"2-0": 0, "2-1": 0, "0-2": 0, "1-2": 0}

    for _ in range(runs):
        wins_a = 0
        wins_b = 0
        for round_idx in range(1, 4):
            fatigue = (round_idx - 1) * fatigue_seconds if fatigue_enabled else 0.0
            time_a = np.random.normal(mu_a + fatigue, sigma_a)
            time_b = np.random.normal(mu_b + fatigue, sigma_b)
            if time_a <= time_b:
                wins_a += 1
            else:
                wins_b += 1
            if wins_a == 2 or wins_b == 2:
                break

        if wins_a > wins_b:
            series_wins[name_a] += 1
            score = "2-0" if wins_b == 0 else "2-1"
        else:
            series_wins[name_b] += 1
            score = "0-2" if wins_a == 0 else "1-2"
        score_counts[score] += 1

    print("\n" + "=" * 70)
    print("  BEST-OF-3 HEAD-TO-HEAD")
    print("=" * 70)
    print(f"Matchup: {name_a} vs {name_b}")
    print(f"Series sims: {runs:,}")
    print(f"{name_a}: {series_wins[name_a] / runs * 100:.1f}% series win")
    print(f"{name_b}: {series_wins[name_b] / runs * 100:.1f}% series win")
    print("Score distribution:")
    for score, count in score_counts.items():
        print(f"  {score}: {count / runs * 100:.1f}%")
    print("-" * 70)


def _run_bracket_simulation(analysis: Dict, predictions: List[Dict], options: Dict):
    if len(predictions) < 2:
        return

    stats = analysis.get("competitor_time_stats", {})
    ranked = sorted(predictions, key=lambda x: x["predicted_time"])
    seeds = {pred["name"]: i + 1 for i, pred in enumerate(ranked)}
    names_by_seed = {seed: name for name, seed in seeds.items()}

    bracket_size = 1
    while bracket_size < len(predictions):
        bracket_size *= 2

    order = _seed_order(bracket_size)

    runs = options.get("bracket_sim_runs", 100000)
    fatigue_enabled = options.get("fatigue_enabled", False)
    fatigue_seconds = options.get("fatigue_seconds", 0.2)

    win_counts = {pred["name"]: 0 for pred in predictions}
    finals_counts = {pred["name"]: 0 for pred in predictions}

    for _ in range(runs):
        current = []
        for i in range(0, bracket_size, 2):
            seed_a = order[i]
            seed_b = order[i + 1]
            current.append((names_by_seed.get(seed_a), names_by_seed.get(seed_b)))

        round_num = 1
        while True:
            next_round = []
            for name_a, name_b in current:
                if name_a and not name_b:
                    winner = name_a
                elif name_b and not name_a:
                    winner = name_b
                else:
                    mu_a = stats.get(name_a, {}).get("mean")
                    mu_b = stats.get(name_b, {}).get("mean")
                    sigma_a = stats.get(name_a, {}).get("std_dev")
                    sigma_b = stats.get(name_b, {}).get("std_dev")
                    if mu_a is None or mu_b is None or sigma_a is None or sigma_b is None:
                        winner = name_a
                    else:
                        fatigue = (round_num - 1) * fatigue_seconds if fatigue_enabled else 0.0
                        time_a = np.random.normal(mu_a + fatigue, sigma_a)
                        time_b = np.random.normal(mu_b + fatigue, sigma_b)
                        winner = name_a if time_a <= time_b else name_b

                next_round.append(winner)

            if len(next_round) == 1:
                win_counts[next_round[0]] += 1
                break

            if len(next_round) == 2:
                finals_counts[next_round[0]] += 1
                finals_counts[next_round[1]] += 1

            current = [(next_round[i], next_round[i + 1]) for i in range(0, len(next_round), 2)]
            round_num += 1

    print("\n" + "=" * 70)
    print("  BRACKET SIMULATION RESULTS")
    print("=" * 70)
    print(f"Simulated brackets: {runs:,}")
    ranked_wins = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
    for name, count in ranked_wins[:8]:
        win_pct = count / runs * 100
        finals_pct = finals_counts.get(name, 0) / runs * 100
        print(f"{name:24s} Win {win_pct:6.2f}% | Finals {finals_pct:6.2f}%")
    print("-" * 70)


def _display_championship_detailed_analysis(analysis: Dict, predictions: List[Dict]):
    """
    Display detailed championship analysis based on Monte Carlo results.
    """
    winner_pcts = analysis["winner_percentages"]
    podium_pcts = analysis.get("podium_percentages", {})
    avg_positions = analysis.get("avg_finish_positions", {})
    stats = analysis.get("competitor_time_stats", {})

    ranked = sorted(winner_pcts.items(), key=lambda x: x[1], reverse=True)
    favorite, favorite_pct = ranked[0]
    runner_up, runner_up_pct = ranked[1] if len(ranked) > 1 else (None, 0.0)

    win_spread = max(winner_pcts.values()) - min(winner_pcts.values())
    parity_index = max(0.0, 100.0 - win_spread)

    tight_prob = analysis.get("tight_finish_prob", 0.0)
    very_tight_prob = analysis.get("very_tight_finish_prob", 0.0)

    print("\n" + "=" * 70)
    print("  CHAMPIONSHIP ANALYSIS")
    print("=" * 70)
    print(f"Favorite: {favorite} ({favorite_pct:.1f}% win)")
    if runner_up:
        print(f"Next best: {runner_up} ({runner_up_pct:.1f}% win)")
    print(f"Parity index: {parity_index:.1f} (lower = more top-heavy)")
    print(f"Win-rate spread: {win_spread:.1f}%")
    print(f"Tight finish chance (<=10s): {tight_prob:.1f}%")
    print(f"Very tight finish chance (<=5s): {very_tight_prob:.1f}%")

    # Additional metrics
    num_competitors = len(winner_pcts)
    entropy = 0.0
    for pct in winner_pcts.values():
        p = pct / 100.0
        if p > 0.0:
            entropy -= p * math.log2(p)
    max_entropy = math.log2(num_competitors) if num_competitors > 1 else 1.0
    entropy_norm = (entropy / max_entropy) * 100.0 if max_entropy else 0.0

    predicted_order = sorted(predictions, key=lambda x: x["predicted_time"])
    predicted_rank = {pred["name"]: i + 1 for i, pred in enumerate(predicted_order)}
    avg_improvements = []
    for name, avg_pos in avg_positions.items():
        pred_rank = predicted_rank.get(name)
        if pred_rank is not None:
            avg_improvements.append(pred_rank - avg_pos)
    avg_comeback = sum(avg_improvements) / len(avg_improvements) if avg_improvements else 0.0

    upsets = 0.0
    for name, pct in winner_pcts.items():
        if predicted_rank.get(name, 999) > 3:
            upsets += pct

    std_devs = [stats.get(name, {}).get("std_dev") for name in stats.keys()]
    std_devs = [val for val in std_devs if isinstance(val, (int, float))]
    consistency_gap = (max(std_devs) - min(std_devs)) if std_devs else 0.0

    most_common_order = analysis.get("most_common_order")
    most_common_order_pct = analysis.get("most_common_order_pct")
    order_scope = analysis.get("most_common_order_scope")

    print("\nAdditional metrics:")
    print(f"  Win-rate entropy: {entropy:.3f} (normalized {entropy_norm:.1f}%)")
    print(f"  Upset frequency (non-top-3 seed wins): {upsets:.1f}%")
    print(f"  Average comeback distance: {avg_comeback:.2f} positions (positive = outperform)")
    if most_common_order:
        order_label = " > ".join(most_common_order)
        scope_label = "full order" if order_scope == "full" else "podium order"
        print(f"  Most common {scope_label}: {order_label} ({most_common_order_pct:.2f}%)")
    else:
        print("  Most common order: N/A")
    print(f"  Consistency gap (max-min std dev): {consistency_gap:.2f}s")

    print("\nTop 5 by win rate:")
    for name, pct in ranked[:5]:
        avg_pos = avg_positions.get(name, 0.0)
        podium = podium_pcts.get(name, 0.0)
        stdev = stats.get(name, {}).get("std_dev", 0.0)
        print(f"  {name:24s} Win {pct:6.2f}% | Podium {podium:6.2f}% | Avg Pos {avg_pos:5.2f} | SD {stdev:5.2f}s")

    print("\n" + "=" * 70)


def _seed_order(bracket_size: int) -> List[int]:
    """Return standard seed order for a power-of-two bracket size."""
    order = [1, 2]
    size = 2
    while size < bracket_size:
        size *= 2
        new_order = []
        for seed in order:
            new_order.append(seed)
            new_order.append(size + 1 - seed)
        order = new_order
    return order


def _win_probability_from_stats(name_a: str, name_b: str, stats: Dict[str, Dict[str, float]]) -> float:
    """Approximate head-to-head win probability using normal distributions."""
    mu_a = stats.get(name_a, {}).get("mean")
    mu_b = stats.get(name_b, {}).get("mean")
    sigma_a = stats.get(name_a, {}).get("std_dev")
    sigma_b = stats.get(name_b, {}).get("std_dev")

    if mu_a is None or mu_b is None:
        return 0.5

    if sigma_a is None or sigma_b is None:
        return 0.5

    sigma = math.sqrt(sigma_a**2 + sigma_b**2)
    if sigma == 0:
        return 1.0 if mu_a < mu_b else 0.0

    # P(A faster than B) = Phi((mu_b - mu_a) / sigma)
    z = (mu_b - mu_a) / sigma
    prob = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(0.0, min(1.0, prob))


def _display_bracket_projection(analysis: Dict, predictions: List[Dict]):
    """
    Display a simple bracket projection using simulated finish-time stats.
    """
    if len(predictions) < 2:
        return

    stats = analysis.get("competitor_time_stats", {})
    ranked = sorted(predictions, key=lambda x: x["predicted_time"])
    seeds = {pred["name"]: i + 1 for i, pred in enumerate(ranked)}
    names_by_seed = {seed: name for name, seed in seeds.items()}

    bracket_size = 1
    while bracket_size < len(predictions):
        bracket_size *= 2

    order = _seed_order(bracket_size)

    print("\n" + "=" * 70)
    print("  BRACKET PROJECTION")
    print("=" * 70)
    print(f"Bracket size: {bracket_size} (seeds 1-{len(predictions)}; byes included)")

    round_num = 1
    current = []
    for i in range(0, bracket_size, 2):
        seed_a = order[i]
        seed_b = order[i + 1]
        name_a = names_by_seed.get(seed_a)
        name_b = names_by_seed.get(seed_b)
        current.append((name_a, name_b))

    while len(current) >= 1:
        print(f"\nRound {round_num}:")
        next_round = []
        for match in current:
            name_a, name_b = match
            if name_a and not name_b:
                print(f"  {name_a} gets a bye")
                winner = name_a
                win_prob = 1.0
            elif name_b and not name_a:
                print(f"  {name_b} gets a bye")
                winner = name_b
                win_prob = 1.0
            else:
                win_prob = _win_probability_from_stats(name_a, name_b, stats)
                winner = name_a if win_prob >= 0.5 else name_b
                print(f"  {name_a} vs {name_b} -> {winner} ({win_prob * 100:5.1f}% win)")

            next_round.append(winner)

        if len(next_round) == 1:
            print(f"\nProjected Champion: {next_round[0]}")
            break

        # Pair winners for next round
        current = [(next_round[i], next_round[i + 1]) for i in range(0, len(next_round), 2)]
        round_num += 1

    print("\n" + "=" * 70)


def _configure_competitor_woods(selected_df, base_wood: Dict) -> Dict[str, Dict]:
    """
    Configure per-competitor wood settings with bulk edit + overrides.

    Returns:
        dict mapping competitor name -> wood dict, or None if cancelled.
    """

    def _parse_indices(selection: str, max_index: int) -> List[int]:
        indices = set()
        for part in selection.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-")
                start_idx = int(start) - 1
                end_idx = int(end) - 1
                for i in range(start_idx, end_idx + 1):
                    if 0 <= i < max_index:
                        indices.add(i)
            else:
                idx = int(part) - 1
                if 0 <= idx < max_index:
                    indices.add(idx)
        return sorted(indices)

    base = dict(base_wood)
    print("\nCurrent race wood applies to all by default.")
    same = input("Use same wood for all competitors? (y/n): ").strip().lower()
    if same in ("", "y"):
        return {row["competitor_name"]: dict(base) for _, row in selected_df.iterrows()}

    while True:
        print("\nCUSTOM WOOD OPTIONS:")
        print("  1) Use race wood as base, then override individuals")
        print("  2) Set a new base wood for everyone, then override individuals")
        print("  3) Cancel")
        choice = input("Choose an option (1-3): ").strip()

        if choice == "1":
            break
        if choice == "2":
            print("\nSet base wood for all competitors:")
            base = wood_menu(dict(base))
            base["event"] = base_wood.get("event")
            break
        if choice == "3" or choice == "":
            return None
        print("Invalid selection. Try again.")

    # Start with base wood for everyone
    wood_map = {row["competitor_name"]: dict(base) for _, row in selected_df.iterrows()}

    # Optional overrides
    print("\nSelect competitors to override (optional).")
    print("Enter numbers (comma/range), or press Enter to skip overrides.")
    for idx, row in enumerate(selected_df.iterrows(), 1):
        _, data = row
        name = data.get("competitor_name", "Unknown")
        print(f"  {idx:3d}) {name}")

    selection = input("\nOverride competitor numbers: ").strip()
    if selection == "":
        return wood_map

    try:
        indices = _parse_indices(selection, len(selected_df))
    except ValueError:
        print("Invalid input. No overrides applied.")
        return wood_map

    for idx in indices:
        name = selected_df.iloc[idx]["competitor_name"]
        print(f"\nOverride wood for {name}:")
        override = wood_menu(dict(base))
        override["event"] = base_wood.get("event")
        wood_map[name] = override

    return wood_map
