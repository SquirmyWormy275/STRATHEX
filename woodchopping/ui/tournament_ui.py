"""Tournament management UI functions.

This module handles multi-round tournament operations including:
- Tournament scenario calculation
- Heat distribution
- Advancer selection
- Round generation
- Tournament state management
"""

import copy
import json
import random
import time
from math import ceil
from typing import Dict, List, Optional

import pandas as pd


def find_optimal_heat_configuration(num_stands: int, tentative_competitors: int, target_advancers: int) -> Dict:
    """Find optimal stands_per_heat to create balanced heats.

    Args:
        num_stands: Total available stands
        tentative_competitors: Expected number of competitors
        target_advancers: Target number of total advancers needed (e.g., num_stands for finals)

    Returns:
        dict: Optimal configuration with stands_per_heat, num_heats, advancers_per_heat, etc.
    """
    # Can't advance more competitors than we have!
    target_advancers = min(target_advancers, tentative_competitors)

    best_config = None
    best_score = float("inf")

    # Try different stands_per_heat from num_stands down to a reasonable minimum
    # Don't go below 50% of available stands (wasteful) or below 3 (too small)
    min_stands_per_heat = max(3, num_stands // 2)

    for stands_per_heat in range(num_stands, min_stands_per_heat - 1, -1):
        num_heats = ceil(tentative_competitors / stands_per_heat)

        # Must have at least 2 heats for a tournament format
        if num_heats < 2:
            continue

        # Calculate heat size distribution
        tentative_competitors // stands_per_heat
        partial_heat_size = tentative_competitors % stands_per_heat

        # Calculate imbalance (smaller is better)
        if partial_heat_size == 0:
            imbalance = 0  # Perfect balance!
            smallest_heat = stands_per_heat
        else:
            imbalance = stands_per_heat - partial_heat_size
            smallest_heat = partial_heat_size

        # Calculate how many should advance from each heat
        advancers_per_heat = target_advancers // num_heats
        total_advancers = advancers_per_heat * num_heats

        # If we're not filling the target well enough, bump up advancers
        if total_advancers < target_advancers * 0.6:
            advancers_per_heat += 1
            total_advancers = advancers_per_heat * num_heats

        # Validation: Can't advance more people than smallest heat has
        if advancers_per_heat > smallest_heat:
            continue

        # Validation: Can't have more advancers than target capacity
        if total_advancers > target_advancers:
            continue

        # Score this configuration (lower is better)
        # Prioritize balance, then fewer heats to reduce schedule length
        fill_penalty = abs(target_advancers - total_advancers)
        heat_penalty = num_heats * 10
        score = imbalance * 100 + heat_penalty + fill_penalty

        if score < best_score:
            best_score = score
            best_config = {
                "stands_per_heat": stands_per_heat,
                "num_heats": num_heats,
                "advancers_per_heat": advancers_per_heat,
                "max_competitors": num_heats * stands_per_heat,
                "imbalance": imbalance,
                "total_advancers": total_advancers,
            }

    # Fallback: if no valid config found, use all stands (old behavior)
    if best_config is None:
        num_heats = max(ceil(tentative_competitors / num_stands), 2)
        advancers_per_heat = target_advancers // num_heats
        if advancers_per_heat * num_heats < target_advancers * 0.5:
            advancers_per_heat += 1

        best_config = {
            "stands_per_heat": num_stands,
            "num_heats": num_heats,
            "advancers_per_heat": advancers_per_heat,
            "max_competitors": num_heats * num_stands,
            "imbalance": tentative_competitors % num_stands,
            "total_advancers": advancers_per_heat * num_heats,
        }

    return best_config


def calculate_tournament_scenarios(num_stands: int, tentative_competitors: int) -> Dict:
    """Calculate three tournament format scenarios based on stands and competitor count.

    Args:
        num_stands: Available chopping stands
        tentative_competitors: Judge's estimate of competitor count

    Returns:
        dict: Contains all scenario options with format:
            {
                'single_heat': {scenario details},
                'heats_to_finals': {scenario details},
                'heats_to_semis_to_finals': {scenario details}
            }
    """

    # SCENARIO 0: Single Heat Mode
    # Strategy: One heat only, perfect for practice/testing/small casual events
    scenario_0 = {
        "max_competitors": num_stands,
        "num_heats": 1,
        "num_semis": 0,
        "num_finals": 0,
        "advancers_per_heat": 0,  # No one advances, it's just one heat
        "total_blocks": num_stands,
        "description": (
            f"Single heat with up to {num_stands} competitors\n"
            f"  -> Perfect for training, testing, or casual events\n"
            f"  -> Results can still be saved to build historical data\n"
            f"  -> No advancement rounds"
        ),
    }

    # SCENARIO 1: Heats -> Finals
    # Strategy: Find optimal stands_per_heat for balanced heats, advance top N to finals
    config_s1 = find_optimal_heat_configuration(num_stands, tentative_competitors, num_stands)

    total_blocks_s1 = tentative_competitors + num_stands

    scenario_1 = {
        "max_competitors": config_s1["max_competitors"],
        "num_heats": config_s1["num_heats"],
        "num_semis": 0,
        "num_finals": 1,
        "advancers_per_heat": config_s1["advancers_per_heat"],
        "stands_per_heat": config_s1["stands_per_heat"],  # NEW: Track actual stands used
        "total_blocks": total_blocks_s1,
        "description": (
            f"{config_s1['num_heats']} heats of {config_s1['stands_per_heat']} "
            f"(max {config_s1['max_competitors']} competitors)\n"
            f"  -> Top {config_s1['advancers_per_heat']} from each heat advance\n"
            f"  -> {config_s1['total_advancers']}-person Final"
        ),
    }

    # SCENARIO 2: Heats -> Semis -> Finals
    # Strategy: Find optimal stands_per_heat for balanced heats, advance to 2 semis, then finals
    num_semis = 2
    semi_total = num_semis * num_stands  # Target: fill 2 semis with num_stands each

    config_s2 = find_optimal_heat_configuration(num_stands, tentative_competitors, semi_total)

    advancers_per_semi = num_stands // num_semis
    total_blocks_s2 = tentative_competitors + semi_total + num_stands

    scenario_2 = {
        "max_competitors": config_s2["max_competitors"],
        "num_heats": config_s2["num_heats"],
        "num_semis": num_semis,
        "num_finals": 1,
        "advancers_per_heat": config_s2["advancers_per_heat"],
        "advancers_per_semi": advancers_per_semi,
        "stands_per_heat": config_s2["stands_per_heat"],  # NEW: Track actual stands used
        "semi_total": config_s2["total_advancers"],  # Actual advancers (may be less than semi_total)
        "total_blocks": total_blocks_s2,
        "description": (
            f"{config_s2['num_heats']} heats of {config_s2['stands_per_heat']} "
            f"(max {config_s2['max_competitors']} competitors)\n"
            f"  -> Top {config_s2['advancers_per_heat']} from each heat ({config_s2['total_advancers']} total)\n"
            f"  -> {num_semis} semi-finals of {num_stands}\n"
            f"  -> Top {advancers_per_semi} from each semi\n"
            f"  -> {num_stands}-person Final"
        ),
    }

    return {
        "single_heat": scenario_0,
        "heats_to_finals": scenario_1,
        "heats_to_semis_to_finals": scenario_2,
    }


def distribute_competitors_into_heats(
    all_competitors_df: pd.DataFrame, handicap_results: List[Dict], num_stands: int, num_heats: int
) -> List[Dict]:
    """Distribute competitors into balanced heats using snake draft pattern.

    This algorithm ensures fair distribution of skill levels across all heats by:
    1. Sorting competitors by handicap mark (highest = front markers first)
    2. Using snake draft: forward then backward distribution pattern
    3. Automatically handling partial heats with appropriate advancement rules

    Args:
        all_competitors_df: All competitors in tournament
        handicap_results: Results from calculate_ai_enhanced_handicaps()
                         Format: [{'name': ..., 'mark': ..., 'predicted_time': ...}, ...]
        num_stands: Competitors per heat (heat capacity)
        num_heats: Number of heats to create

    Returns:
        list: List of round_object dictionaries, one for each heat
    """

    # Sort competitors by mark (descending: highest mark first = front markers)
    sorted_competitors = sorted(handicap_results, key=lambda x: x["mark"], reverse=True)

    # Initialize empty heats
    heats = []
    for i in range(num_heats):
        heats.append(
            {
                "round_type": "heat",
                "round_number": i + 1,
                "round_name": f"Heat {i + 1}",
                "competitors": [],
                "competitors_df": pd.DataFrame(),
                "handicap_results": [],
                "actual_results": {},
                "advancers": [],
                "num_to_advance": 2,  # Default, will be adjusted for partial heats
                "status": "pending",
            }
        )

    # Snake draft distribution
    heat_index = 0
    direction = 1  # 1 = forward, -1 = backward

    for comp in sorted_competitors:
        heats[heat_index]["competitors"].append(comp["name"])
        heats[heat_index]["handicap_results"].append(comp)

        # Move to next heat
        heat_index += direction

        # Reverse direction at ends (snake pattern)
        if heat_index >= num_heats:
            heat_index = num_heats - 1
            direction = -1
        elif heat_index < 0:
            heat_index = 0
            direction = 1

    # Build competitor DataFrames and set advancement rules for each heat
    for heat in heats:
        # Get DataFrame subset for competitors in this heat
        heat["competitors_df"] = all_competitors_df[
            all_competitors_df["competitor_name"].isin(heat["competitors"])
        ].copy()

        # Determine advancement rules based on heat size
        heat_size = len(heat["competitors"])
        heat_capacity = num_stands
        fill_percentage = heat_size / heat_capacity

        # If heat is <=50% full, only top 1 advances (fairness for partial heats)
        if fill_percentage <= 0.5:
            heat["num_to_advance"] = 1
        else:
            heat["num_to_advance"] = 2

    return heats


def select_heat_advancers(round_object: Dict) -> List[str]:
    """Interactive function for judge to select advancing competitors from a completed heat.

    Args:
        round_object: Round object for completed heat

    Returns:
        list: Names of advancing competitors
    """

    print(f"\n{'=' * 70}")
    print(f"  {round_object['round_name'].upper()} RESULTS & ADVANCERS")
    print(f"{'=' * 70}")

    # Use FINISH ORDER to determine results (critical for handicap racing)

    if round_object.get("finish_order"):
        # Sort by finish order (1st, 2nd, 3rd, etc.)
        sorted_by_finish = sorted(
            round_object["finish_order"].items(),
            key=lambda x: x[1],  # Sort by finish position
        )

        # Display results table with finish position, cutting time, and advancement status
        table_width = 74
        print("\n" + "-" * table_width)
        print(f"{round_object['round_name'].upper()} - FINAL RESULTS".center(table_width))
        print("-" * table_width)
        print("Finish position based on REAL-TIME completion (handicap included)".center(table_width))
        print("-" * table_width)
        print(f"{'Pos':>3} | {'Competitor':<35} | {'Time':>7} | {'Status':<10}")
        print("-" * table_width)

        advancers = []  # Auto-select based on finish order
        draw_eligible = []  # Only NEXT position is draw-eligible (position-based pool)
        next_draw_position = round_object["num_to_advance"] + 1

        for name, finish_pos in sorted_by_finish:
            cutting_time = round_object["actual_results"].get(name, 0)

            # Determine advancement
            advance = ""

            # Auto-select top finishers for advancement
            if finish_pos <= round_object["num_to_advance"]:
                advance = "ADVANCES"
                advancers.append(name)
            elif finish_pos == next_draw_position:
                # Only the NEXT position after auto-advancers is draw-eligible
                draw_eligible.append(name)

            # Format line: Position | Name | Cutting Time | Status
            pos_part = f"{finish_pos:>3}"
            name_part = f"{name[:35]:<35}"
            time_part = f"{cutting_time:>6.2f}s"
            status_part = f"{advance:<10}"

            print(f"{pos_part} | {name_part} | {time_part:>7} | {status_part}")

        print("-" * table_width + "\n")

        # Display advancers summary
        print(f"Top {round_object['num_to_advance']} finisher(s) automatically advance:")
        for name in advancers:
            finish_pos = round_object["finish_order"][name]
            print(f"  {finish_pos}. {name}")

        if draw_eligible:
            # Show only the next position as draw-eligible
            print(f"\nDraw pool (position {next_draw_position}): {', '.join(draw_eligible)}")
            round_object["draw_eligible"] = draw_eligible

        # Allow judge to override if needed
        override = input("\nAccept these advancers? (y/n to manually select): ").strip().lower()

        if override == "y" or override == "":
            # Accept auto-selected advancers
            round_object["advancers"] = advancers
            round_object["status"] = "completed"
            return advancers
        else:
            # Manual override - let judge pick
            print("\nManual selection mode:")
            advancers = []
            while len(advancers) < round_object["num_to_advance"]:
                try:
                    for i, (name, pos) in enumerate(sorted_by_finish, 1):
                        print(f"  {i}) {name} (finished {pos})")

                    choice = input(
                        f"\nSelect competitor {len(advancers) + 1} of {round_object['num_to_advance']} (number): "
                    ).strip()
                    idx = int(choice) - 1

                    if 0 <= idx < len(sorted_by_finish):
                        selected = sorted_by_finish[idx][0]
                        if selected not in advancers:
                            advancers.append(selected)
                            print(f"  [OK] {selected} selected")
                        else:
                            print("  Already selected. Choose another competitor.")
                    else:
                        print(f"  Invalid number. Enter 1-{len(sorted_by_finish)}")

                except ValueError:
                    print("  Please enter a valid number.")

            # Position-based draw pool: only next position after num_to_advance
            draw_eligible = [
                name for name, pos in sorted_by_finish if name not in advancers and pos == next_draw_position
            ]
            if draw_eligible:
                round_object["draw_eligible"] = draw_eligible

    else:
        # Fallback: No finish order recorded (legacy mode - use raw times)
        print("WARNING: No finish order recorded. Using raw cutting times (may be inaccurate for handicap).")

        if round_object["actual_results"]:
            sorted_results = sorted(
                round_object["actual_results"].items(),
                key=lambda x: x[1],  # Sort by raw time
            )

            print("Competitors (sorted by cutting time):")
            for i, (name, time) in enumerate(sorted_results, 1):
                print(f"  {i}) {name:30s} {time:.2f}s")
        else:
            print("Competitors in heat:")
            for i, name in enumerate(round_object["competitors"], 1):
                print(f"  {i}) {name}")

        # Manual selection
        advancers = []
        while len(advancers) < round_object["num_to_advance"]:
            try:
                choice = input(
                    f"\nSelect competitor {len(advancers) + 1} of {round_object['num_to_advance']} (number): "
                ).strip()

                if choice == "":
                    print("Selection cannot be blank. Please enter a number.")
                    continue

                idx = int(choice) - 1

                if 0 <= idx < len(round_object["competitors"]):
                    selected = round_object["competitors"][idx]
                    if selected not in advancers:
                        advancers.append(selected)
                        print(f"  [OK] {selected} selected")
                    else:
                        print("  Already selected. Choose another competitor.")
                else:
                    print(f"  Invalid number. Enter 1-{len(round_object['competitors'])}")

            except ValueError:
                print("  Please enter a valid number.")

    # Update round object
    round_object["advancers"] = advancers
    round_object["status"] = "completed"

    return advancers


def _build_finish_positions(round_object: Dict) -> Dict[str, int]:
    finish_order = round_object.get("finish_order") or {}
    if finish_order:
        return finish_order

    actual_results = round_object.get("actual_results") or {}
    if actual_results:
        sorted_results = sorted(actual_results.items(), key=lambda x: x[1])
        return {name: idx + 1 for idx, (name, _) in enumerate(sorted_results)}

    return {}


def _format_slot_name(name: str, width: int) -> str:
    clean = str(name)
    if len(clean) > width:
        if width <= 3:
            return clean[:width]
        return clean[: width - 3] + "..."
    return clean.ljust(width)


def _run_slot_machine_animation(winners: List[str], candidates: List[str], rng: random.Random) -> None:
    if not winners or not candidates:
        return

    width = 18
    frames = 12
    delay = 0.08

    print("\n" + "=" * (width * 3 + 10))
    print("  SLOT MACHINE DRAW")
    print("=" * (width * 3 + 10))

    for winner in winners:
        for i in range(frames):
            left = rng.choice(candidates)
            middle = rng.choice(candidates)
            right = rng.choice(candidates)
            if i == frames - 1:
                middle = winner
            line = (
                f"  [ {_format_slot_name(left, width)} ]"
                f" [ {_format_slot_name(middle, width)} ]"
                f" [ {_format_slot_name(right, width)} ]"
            )
            print(line, end="\r", flush=True)
            time.sleep(delay)
        print("")
        print(f"  WINNER: {winner}")

    print("=" * (width * 3 + 10))


def fill_advancers_with_random_draw(
    rounds: List[Dict],
    all_advancers: List[str],
    target_count: Optional[int],
    round_label: str = "next round",
) -> List[str]:
    """Fill remaining advancement slots by random draw from next-place finishers."""
    if not target_count or len(all_advancers) >= target_count:
        return all_advancers

    remaining = target_count - len(all_advancers)
    print(f"\nNeed {remaining} more advancer(s) to fill the {round_label} ({target_count} slots).")

    position_pool: Dict[int, List[str]] = {}
    missing_finish_orders = 0

    for round_obj in rounds:
        finish_positions = _build_finish_positions(round_obj)
        if not finish_positions:
            missing_finish_orders += 1
            continue

        num_to_advance = round_obj.get("num_to_advance", 0)
        for name, pos in finish_positions.items():
            if pos <= num_to_advance:
                continue
            if name in all_advancers:
                continue
            position_pool.setdefault(pos, []).append(name)

    if not position_pool:
        print("No eligible finishers available for a random draw.")
        return all_advancers

    print("\n+-----------------------------------------------------------------+")
    print("|  POSITION-BASED DRAW POOL                                       |")
    print("|  (Slots filled from lowest position first, then next position)  |")
    print("+-----------------------------------------------------------------+")
    print("\nEligible finishers by position:")
    for pos in sorted(position_pool):
        names = ", ".join(position_pool[pos])
        print(f"  Position {pos}: {len(position_pool[pos])} candidate(s) -> {names}")
    if missing_finish_orders:
        print(f"Note: {missing_finish_orders} heat(s) missing finish order data were skipped.")

    choice = input("\nFill remaining slots with a random draw? (y/n): ").strip().lower()
    if choice not in ("y", ""):
        return all_advancers

    seed_input = input("Optional random seed (press Enter to skip): ").strip()
    rng = random.Random()
    if seed_input:
        try:
            rng.seed(int(seed_input))
        except ValueError:
            rng.seed(seed_input)

    print("\nDrawing", end="", flush=True)
    for _ in range(6):
        time.sleep(0.15)
        print(".", end="", flush=True)
    print("")

    selected = []
    slots_left = remaining
    positions_used = []
    for pos in sorted(position_pool):
        if slots_left <= 0:
            break
        candidates = position_pool[pos]
        if not candidates:
            continue
        if len(candidates) <= slots_left:
            # All candidates at this position advance (no draw needed)
            chosen = candidates[:]
            if len(candidates) > 1:
                print(f"\n  All {len(candidates)} competitors at position {pos} advance (no draw needed)")
        else:
            # Random draw required - more candidates than slots
            print(f"\n  Drawing {slots_left} from {len(candidates)} candidates at position {pos}...")
            chosen = rng.sample(candidates, slots_left)
        selected.extend(chosen)
        positions_used.append(pos)
        slots_left -= len(chosen)

    if not selected:
        print("No additional advancers were selected.")
        return all_advancers

    flat_candidates = []
    for pos in sorted(position_pool):
        flat_candidates.extend(position_pool[pos])

    _run_slot_machine_animation(selected, flat_candidates, rng)

    all_advancers.extend(selected)
    print("\nRandom draw selected:")
    for name in selected:
        print(f"  - {name}")

    if slots_left > 0:
        print(f"\nWarning: {slots_left} slot(s) remain unfilled due to limited candidates.")

    return all_advancers


def extract_tournament_results(tournament_state: Dict) -> Dict[str, float]:
    """Extract actual cutting times from completed tournament rounds.

    This function collects all recorded times from heats/semis that have been completed.
    These times represent performance on the SAME wood being used throughout the tournament,
    making them the most accurate predictor for subsequent rounds.

    Args:
        tournament_state: Global tournament state containing all rounds

    Returns:
        dict: {competitor_name: actual_cutting_time, ...}
              Only includes competitors who have completed times recorded
    """
    tournament_results = {}

    for round_obj in tournament_state.get("rounds", []):
        # Only use completed rounds
        if round_obj.get("status") == "completed":
            # Extract actual results (cutting times)
            for competitor_name, cutting_time in round_obj.get("actual_results", {}).items():
                # Use the most recent time if competitor appeared in multiple rounds
                # (e.g., if semis already completed and generating finals)
                tournament_results[competitor_name] = cutting_time

    return tournament_results


def generate_next_round(
    tournament_state: Dict,
    all_advancers: List[str],
    next_round_type: str,
    is_championship: bool = False,
    animate_selection: bool = False,
) -> List[Dict]:
    """Generate semi-final or final rounds from advancing competitors.

    CRITICAL ENHANCEMENT: This function now RECALCULATES handicaps using actual times
    from completed rounds in THIS TOURNAMENT. Since the wood is identical across all rounds,
    these same-tournament results are weighted at 97% vs historical data (3%), providing
    the most accurate handicaps possible.

    Args:
        tournament_state: Global tournament state
        all_advancers: All competitors advancing from previous round
        next_round_type: 'semi' or 'final'
        is_championship: If True, skip handicap recalculation (Championship event - all Mark 3)

    Returns:
        list: List of round_object dictionaries for next stage with RECALCULATED handicaps
    """

    if animate_selection and all_advancers:
        rng = random.Random()
        _run_slot_machine_animation(all_advancers, all_advancers, rng)

    # Extract actual cutting times from completed rounds (NEW - critical improvement)
    tournament_results = extract_tournament_results(tournament_state)

    # Skip recalculation for Championship events (everyone stays at Mark 3)
    if is_championship:
        print(f"\n{'=' * 70}")
        print("  CHAMPIONSHIP EVENT - PRESERVING MARK 3")
        print(f"{'=' * 70}")
        print(f"\nAll {len(all_advancers)} advancers keep Mark 3 (fastest time wins)")

        # Create simple handicap results with Mark 3
        advancer_results = []
        for comp_name in all_advancers:
            advancer_results.append(
                {
                    "name": comp_name,
                    "predicted_time": 0.0,  # Not used for championship
                    "method_used": "Championship",
                    "confidence": "N/A",
                    "explanation": "Championship event: fastest time wins",
                    "predictions": {},
                    "mark": 3,
                }
            )

        print("[OK] Championship marks assigned for next round")
        print(f"{'=' * 70}\n")

        # Skip to heat distribution
        num_stands = tournament_state["num_stands"]
        all_advancers_df = tournament_state["all_competitors_df"][
            tournament_state["all_competitors_df"]["competitor_name"].isin(all_advancers)
        ].copy()

        # Determine optimal heat configuration based on round type
        if next_round_type == "final":
            # Finals: Always 1 heat using all available stands
            stands_per_heat = num_stands
            num_heats = 1
        elif next_round_type == "semi":
            # Semi-finals: Optimize stands per heat for balanced heats
            # Target: Fill finals (num_stands competitors)
            optimal_config = find_optimal_heat_configuration(num_stands, len(all_advancers), num_stands)
            stands_per_heat = optimal_config["stands_per_heat"]
            num_heats = optimal_config["num_heats"]
        else:
            # Other rounds: Use basic calculation with optimization
            optimal_config = find_optimal_heat_configuration(num_stands, len(all_advancers), num_stands)
            stands_per_heat = optimal_config["stands_per_heat"]
            num_heats = optimal_config["num_heats"]

        next_rounds = distribute_competitors_into_heats(
            all_advancers_df,
            advancer_results,
            stands_per_heat,  # Use optimal stands per heat
            num_heats,
        )

        # Update round type and names
        for i, round_obj in enumerate(next_rounds):
            round_obj["round_type"] = next_round_type
            if next_round_type == "final":
                round_obj["round_name"] = "Final"
                round_obj["round_number"] = 1
            elif next_round_type == "semi":
                round_obj["round_name"] = f"Semi {i + 1}"
                round_obj["round_number"] = i + 1

        return next_rounds

    # Handicap event: full recalculation with tournament weighting
    print(f"\n{'=' * 70}")
    print("  RECALCULATING HANDICAPS USING TOURNAMENT RESULTS")
    print(f"{'=' * 70}")
    print("\nUsing actual times from completed rounds (97% weight):")
    for name, t in tournament_results.items():
        if name in all_advancers:
            print(f"  - {name}: {t:.2f}s")

    # Import handicap calculation function
    from woodchopping.data import load_results_df
    from woodchopping.handicaps import calculate_ai_enhanced_handicaps

    # Get DataFrame for advancers only
    all_advancers_df = tournament_state["all_competitors_df"][
        tournament_state["all_competitors_df"]["competitor_name"].isin(all_advancers)
    ].copy()

    # RECALCULATE handicaps with tournament results prioritized
    # Check if wood characteristics are stored (v4.4+)
    wood_species = tournament_state.get("wood_species")
    wood_diameter = tournament_state.get("wood_diameter")
    wood_quality = tournament_state.get("wood_quality")
    event_code = tournament_state.get("event_code")

    if not all([wood_species, wood_diameter, event_code is not None, wood_quality is not None]):
        print("\n[WARN] WARNING: Wood characteristics not found in tournament state.")
        print("Cannot recalculate handicaps using tournament results.")
        print("Using original handicaps from initial calculation.")

        # Fallback: extract handicap results from previous rounds
        all_results = []
        for round_obj in tournament_state["rounds"]:
            if "handicap_results" in round_obj and round_obj["handicap_results"]:
                all_results.extend(round_obj["handicap_results"])

        advancer_results = [r for r in all_results if r["name"] in all_advancers]
    else:
        # Normal path: recalculate with tournament weighting
        results_df = load_results_df()

        # Calculate new handicaps with tournament result weighting
        advancer_results = calculate_ai_enhanced_handicaps(
            all_advancers_df,
            wood_species,
            wood_diameter,
            wood_quality,
            event_code,
            results_df,
            tournament_results=tournament_results,  # NEW parameter for same-tournament weighting
        )

    print("\n[OK] Handicaps recalculated using tournament performance data")
    print(f"{'=' * 70}\n")

    # Determine optimal heat configuration for next round
    num_stands = tournament_state["num_stands"]

    # Determine optimal heat configuration based on round type
    if next_round_type == "final":
        # Finals: Always 1 heat using all available stands
        stands_per_heat = num_stands
        num_heats = 1
    elif next_round_type == "semi":
        # Semi-finals: Optimize stands per heat for balanced heats
        # Target: Fill finals (num_stands competitors)
        optimal_config = find_optimal_heat_configuration(num_stands, len(all_advancers), num_stands)
        stands_per_heat = optimal_config["stands_per_heat"]
        num_heats = optimal_config["num_heats"]
    else:
        # Other rounds: Use basic calculation with optimization
        optimal_config = find_optimal_heat_configuration(num_stands, len(all_advancers), num_stands)
        stands_per_heat = optimal_config["stands_per_heat"]
        num_heats = optimal_config["num_heats"]

    # Use same distribution algorithm (snake draft) with RECALCULATED handicaps
    next_rounds = distribute_competitors_into_heats(
        all_advancers_df,
        advancer_results,  # Now contains recalculated handicaps using tournament data
        stands_per_heat,  # Use optimal stands per heat
        num_heats,
    )

    # Update round type and names
    for i, round_obj in enumerate(next_rounds):
        round_obj["round_type"] = next_round_type
        if next_round_type == "final":
            round_obj["round_name"] = "Final"
            round_obj["round_number"] = 1
        elif next_round_type == "semi":
            round_obj["round_name"] = f"Semi {i + 1}"
            round_obj["round_number"] = i + 1

    return next_rounds


def view_tournament_status(tournament_state: Dict) -> None:
    """Display visual tournament bracket showing progress and results.

    Args:
        tournament_state: Global tournament state
    """

    print(f"\n{'=' * 70}")
    print("  TOURNAMENT STATUS")
    print(f"{'=' * 70}")

    if not tournament_state.get("rounds"):
        print("\nNo tournament rounds generated yet.")
        return

    print(f"\nEvent: {tournament_state.get('event_name', 'Unnamed Event')}")
    print(f"Format: {tournament_state.get('format', 'Unknown')}")
    print(f"Stands: {tournament_state.get('num_stands', '?')}")
    print(f"Total Competitors: {len(tournament_state.get('all_competitors', []))}")

    # Group rounds by type
    heats = [r for r in tournament_state["rounds"] if r["round_type"] == "heat"]
    semis = [r for r in tournament_state["rounds"] if r["round_type"] == "semi"]
    finals = [r for r in tournament_state["rounds"] if r["round_type"] == "final"]

    # Display heats
    if heats:
        print(f"\n{'-' * 70}")
        print(f"INITIAL HEATS ({len(heats)} total)")
        print(f"{'-' * 70}")
        for heat in heats:
            status_icon = "[OK]" if heat["status"] == "completed" else "[ ]"
            print(
                f"{status_icon} {heat['round_name']:15s} - {len(heat['competitors'])} competitors, top {heat['num_to_advance']} advance"
            )
            if heat["status"] == "completed" and heat.get("advancers"):
                print(f"    Advancers: {', '.join(heat['advancers'])}")

    # Display semis
    if semis:
        print(f"\n{'-' * 70}")
        print(f"SEMI-FINALS ({len(semis)} total)")
        print(f"{'-' * 70}")
        for semi in semis:
            status_icon = "[OK]" if semi["status"] == "completed" else "[ ]"
            print(
                f"{status_icon} {semi['round_name']:15s} - {len(semi['competitors'])} competitors, top {semi['num_to_advance']} advance"
            )
            if semi["status"] == "completed" and semi.get("advancers"):
                print(f"    Advancers: {', '.join(semi['advancers'])}")

    # Display finals
    if finals:
        print(f"\n{'-' * 70}")
        print("FINAL")
        print(f"{'-' * 70}")
        for final in finals:
            status_icon = "[OK]" if final["status"] == "completed" else "[ ]"
            print(f"{status_icon} {final['round_name']:15s} - {len(final['competitors'])} competitors")
            if final["status"] == "completed":
                print("    Tournament Complete!")

    print(f"\n{'=' * 70}\n")


def save_tournament_state(tournament_state: Dict, filename: str = "saves/tournament_state.json") -> None:
    """Save tournament state to JSON for crash recovery.

    Args:
        tournament_state: Tournament state to save
        filename: Output filename
    """
    try:
        # Convert DataFrames to dict format for JSON serialization
        state_copy = copy.deepcopy(tournament_state)

        # Convert main competitors DataFrame
        if not state_copy["all_competitors_df"].empty:
            state_copy["all_competitors_df"] = state_copy["all_competitors_df"].to_dict("records")
        else:
            state_copy["all_competitors_df"] = []

        # Convert DataFrames in rounds
        for round_obj in state_copy.get("rounds", []):
            if not round_obj["competitors_df"].empty:
                round_obj["competitors_df"] = round_obj["competitors_df"].to_dict("records")
            else:
                round_obj["competitors_df"] = []

        # Write to file
        with open(filename, "w") as f:
            json.dump(state_copy, f, indent=2, default=str)

        print(f"Tournament state saved to {filename}")

    except Exception as e:
        print(f"Error saving tournament state: {e}")


def load_tournament_state(filename: str = "saves/tournament_state.json") -> Optional[Dict]:
    """Load tournament state from JSON.

    Args:
        filename: Input filename

    Returns:
        dict: Loaded tournament state, or None if error
    """
    try:
        with open(filename, "r") as f:
            state = json.load(f)

        # Convert dict records back to DataFrames
        if state.get("all_competitors_df"):
            state["all_competitors_df"] = pd.DataFrame(state["all_competitors_df"])
        else:
            state["all_competitors_df"] = pd.DataFrame()

        # Convert DataFrames in rounds
        for round_obj in state.get("rounds", []):
            if round_obj.get("competitors_df"):
                round_obj["competitors_df"] = pd.DataFrame(round_obj["competitors_df"])
            else:
                round_obj["competitors_df"] = pd.DataFrame()

        # Backward compatibility: Add payout_config if missing (V4.5)
        if "payout_config" not in state:
            state["payout_config"] = None

        print(f"Tournament state loaded from {filename}")
        return state

    except FileNotFoundError:
        print(f"Tournament state file '{filename}' not found.")
        return None
    except Exception as e:
        print(f"Error loading tournament state: {e}")
        return None


def auto_save_state(tournament_state: Dict) -> None:
    """Auto-save tournament state after significant actions.

    Args:
        tournament_state: Tournament state to save
    """
    save_tournament_state(tournament_state, "saves/tournament_state.json")
