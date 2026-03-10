# -*- coding: utf-8 -*-
"""Head-to-head bracket tournament UI functions.

This module handles single-elimination bracket tournaments where:
- All competitors receive Mark 3 (championship format)
- Matches are 1v1 on 2 stands (head-to-head)
- Seeding based on AI predictions
- Automatic bye placement for non-power-of-2 brackets
- Visual ASCII tree bracket display + HTML export
- Sequential match result entry
- View-only (no Excel writes)
"""

import math
import webbrowser
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd


# ===========================================================================
# BRACKET STRUCTURE & GENERATION
# ===========================================================================

def get_round_info(round_number: int, total_rounds: int) -> Dict[str, str]:
    """Generate round name and code based on position in bracket.

    Args:
        round_number: Current round (1 = first round)
        total_rounds: Total rounds in bracket

    Returns:
        dict: {'round_name': str, 'round_code': str}

    Examples:
        - 32-person bracket (5 rounds): R1=R32, R2=R16, R3=QF, R4=SF, R5=F
        - 16-person bracket (4 rounds): R1=R16, R2=QF, R3=SF, R4=F
        - 8-person bracket (3 rounds): R1=QF, R2=SF, R3=F
    """
    rounds_from_end = total_rounds - round_number

    if rounds_from_end == 0:
        return {'round_name': 'Final', 'round_code': 'F'}
    elif rounds_from_end == 1:
        return {'round_name': 'Semifinals', 'round_code': 'SF'}
    elif rounds_from_end == 2:
        return {'round_name': 'Quarterfinals', 'round_code': 'QF'}
    else:
        # Calculate bracket size for this round
        bracket_size = 2 ** (rounds_from_end + 1)
        return {
            'round_name': f'Round of {bracket_size}',
            'round_code': f'R{bracket_size}'
        }


def calculate_bye_structure(num_competitors: int) -> Dict:
    """Calculate bracket structure with byes for non-power-of-2 competitor counts.

    Strategy:
    - Find next power of 2
    - Calculate number of byes needed
    - Top seeds get byes (standard tournament practice)
    - Byes advance automatically to Round 2

    Args:
        num_competitors: Total competitor count

    Returns:
        dict: {
            'bracket_size': int,          # Next power of 2
            'num_byes': int,              # Number of byes needed
            'first_round_matches': int,   # Actual matches in R1
            'seeds_with_byes': list,      # Seeds that get byes
            'total_rounds': int           # Total rounds needed
        }

    Examples:
        6 competitors: 8-person bracket, 2 byes (seeds 1-2 get byes)
        13 competitors: 16-person bracket, 3 byes (seeds 1-3 get byes)
        17 competitors: 32-person bracket, 15 byes (seeds 1-15 get byes)
    """
    # Find next power of 2
    bracket_size = 2 ** math.ceil(math.log2(num_competitors))

    # Calculate byes
    num_byes = bracket_size - num_competitors

    # Top seeds get byes
    seeds_with_byes = list(range(1, num_byes + 1))

    # First round has actual matches (not byes)
    # Each match has 2 people, so: (people playing) / 2 = matches
    first_round_matches = (num_competitors - num_byes) // 2

    # Total rounds
    total_rounds = int(math.log2(bracket_size))

    return {
        'bracket_size': bracket_size,
        'num_byes': num_byes,
        'first_round_matches': first_round_matches,
        'seeds_with_byes': seeds_with_byes,
        'total_rounds': total_rounds
    }


def generate_standard_bracket_pairings(seeds: List[int]) -> List[Tuple[int, int]]:
    """Generate standard tournament bracket pairings.

    Standard bracket: 1 vs N, 2 vs N-1, 3 vs N-2, etc.
    This ensures top seeds don't meet until later rounds.

    Args:
        seeds: List of seed numbers (already sorted 1, 2, 3, ...)

    Returns:
        List of (seed1, seed2) tuples representing first round matchups

    Example:
        8 seeds: [(1,8), (2,7), (3,6), (4,5)]
        16 seeds: [(1,16), (2,15), (3,14), (4,13), (5,12), (6,11), (7,10), (8,9)]
    """
    n = len(seeds)
    pairings = []

    for i in range(n // 2):
        seed1 = seeds[i]
        seed2 = seeds[n - 1 - i]
        pairings.append((seed1, seed2))

    return pairings


def generate_bracket_with_byes(predictions: Dict) -> List[Dict]:
    """Generate complete bracket structure with bye placement.

    Args:
        predictions: Dict mapping competitor names to prediction dicts with seeds

    Returns:
        List of round objects with matches (including byes)
    """
    # Sort competitors by seed
    sorted_competitors = sorted(
        predictions.items(),
        key=lambda x: x[1]['seed']
    )

    num_competitors = len(sorted_competitors)
    bye_info = calculate_bye_structure(num_competitors)

    # Create seed-to-name mapping
    seed_to_name = {pred['seed']: name for name, pred in predictions.items()}

    # Generate Round 1 with byes
    rounds = []
    round1_matches = []

    match_counter = 1

    # Byes for top seeds
    for seed in bye_info['seeds_with_byes']:
        round1_matches.append({
            'match_id': f"R1-M{match_counter}",
            'match_number': match_counter,
            'competitor1': seed_to_name[seed],
            'competitor2': None,  # Bye
            'seed1': seed,
            'seed2': None,
            'winner': seed_to_name[seed],  # Auto-advance
            'loser': None,
            'time1': None,
            'time2': None,
            'finish_position1': None,
            'finish_position2': None,
            'status': 'bye',
            'advances_to': None,  # Set later when building bracket tree
            'feeds_from': []
        })
        match_counter += 1

    # Actual first-round matches (remaining competitors)
    # Use standard bracket pairing for non-bye competitors
    remaining_seeds = [s for s in range(1, num_competitors + 1)
                       if s not in bye_info['seeds_with_byes']]

    pairings = generate_standard_bracket_pairings(remaining_seeds)

    for seed1, seed2 in pairings:
        round1_matches.append({
            'match_id': f"R1-M{match_counter}",
            'match_number': match_counter,
            'competitor1': seed_to_name[seed1],
            'competitor2': seed_to_name[seed2],
            'seed1': seed1,
            'seed2': seed2,
            'winner': None,
            'loser': None,
            'time1': None,
            'time2': None,
            'finish_position1': None,
            'finish_position2': None,
            'status': 'pending',
            'advances_to': None,
            'feeds_from': []
        })
        match_counter += 1

    round_info = get_round_info(1, bye_info['total_rounds'])
    rounds.append({
        'round_number': 1,
        'round_name': round_info['round_name'],
        'round_code': round_info['round_code'],
        'matches': round1_matches,
        'status': 'in_progress' if round1_matches else 'pending'
    })

    # Generate subsequent rounds (all TBD until R1 completes)
    for round_num in range(2, bye_info['total_rounds'] + 1):
        round_info = get_round_info(round_num, bye_info['total_rounds'])
        num_matches = bye_info['bracket_size'] // (2 ** round_num)

        round_matches = []
        for match_num in range(1, num_matches + 1):
            match_id = f"{round_info['round_code']}-M{match_num}"
            round_matches.append({
                'match_id': match_id,
                'match_number': match_num,
                'competitor1': None,  # TBD
                'competitor2': None,  # TBD
                'seed1': None,
                'seed2': None,
                'winner': None,
                'loser': None,
                'time1': None,
                'time2': None,
                'finish_position1': None,
                'finish_position2': None,
                'status': 'pending',
                'advances_to': None,
                'feeds_from': []
            })

        rounds.append({
            'round_number': round_num,
            'round_name': round_info['round_name'],
            'round_code': round_info['round_code'],
            'matches': round_matches,
            'status': 'pending'
        })

    # Link matches (set advances_to and feeds_from)
    link_bracket_matches(rounds)

    return rounds


def link_bracket_matches(rounds: List[Dict]) -> None:
    """Link matches to show bracket progression (mutates rounds in place).

    Sets 'advances_to' for each match and 'feeds_from' for next round matches.
    """
    for round_idx, round_obj in enumerate(rounds[:-1]):  # All except final
        next_round = rounds[round_idx + 1]

        for match_idx, match in enumerate(round_obj['matches']):
            # Winner advances to next round match
            next_match_idx = match_idx // 2
            next_match = next_round['matches'][next_match_idx]

            match['advances_to'] = next_match['match_id']
            next_match['feeds_from'].append(match['match_id'])


# ===========================================================================
# DOUBLE ELIMINATION BRACKET GENERATION
# ===========================================================================

def generate_double_elimination_bracket(predictions: Dict[str, Dict]) -> Dict:
    """Generate double elimination bracket with winners, losers, and grand finals.

    Args:
        predictions: {competitor_name: prediction_dict_with_seed}

    Returns:
        dict: {
            'winners_rounds': list of winner bracket rounds,
            'losers_rounds': list of loser bracket rounds,
            'grand_finals': grand finals match dict,
            'total_rounds': total number of rounds,
            'total_matches': total number of matches
        }
    """
    # Generate winners bracket (same as single elimination)
    winners_rounds = generate_bracket_with_byes(predictions)

    # Add bracket_type field to all winners matches
    for round_obj in winners_rounds:
        for match in round_obj['matches']:
            match['bracket_type'] = 'winners'

    # Generate losers bracket structure
    losers_rounds = generate_losers_bracket_structure(winners_rounds)

    # Create grand finals match
    grand_finals = create_grand_finals_match()

    # Calculate totals
    total_winners_matches = sum(len(r['matches']) for r in winners_rounds)
    total_losers_matches = sum(len(r['matches']) for r in losers_rounds)
    total_matches = total_winners_matches + total_losers_matches + 1  # +1 for grand finals

    return {
        'winners_rounds': winners_rounds,
        'losers_rounds': losers_rounds,
        'grand_finals': grand_finals,
        'total_rounds': len(winners_rounds) + len(losers_rounds) + 1,
        'total_matches': total_matches
    }


def generate_losers_bracket_structure(winners_rounds: List[Dict]) -> List[Dict]:
    """Generate losers bracket from winners bracket structure.

    Losers bracket progression:
    - After Winners R1: Losers play each other (LR1)
    - After Winners R2: LR1 winners play Winners R2 losers (LR2-LR3)
    - Continue until one survivor remains

    Args:
        winners_rounds: List of winners bracket round objects

    Returns:
        list: Losers bracket round objects
    """
    num_winners_rounds = len(winners_rounds)
    losers_rounds = []
    losers_match_counter = 1

    # Calculate how many competitors will drop from Winners R1
    wr1_matches = [m for m in winners_rounds[0]['matches'] if m['competitor2'] is not None]
    num_wr1_losers = len(wr1_matches)

    # Losers Round 1: Winners R1 losers play each other
    if num_wr1_losers > 1:
        lr1_matches = []
        num_lr1_matches = num_wr1_losers // 2

        for match_num in range(1, num_lr1_matches + 1):
            lr1_matches.append({
                'match_id': f"LR1-M{match_num}",
                'match_number': match_num,
                'competitor1': None,  # TBD from Winners R1 losers
                'competitor2': None,  # TBD from Winners R1 losers
                'seed1': None,
                'seed2': None,
                'winner': None,
                'loser': None,
                'time1': None,
                'time2': None,
                'finish_position1': None,
                'finish_position2': None,
                'status': 'pending',
                'advances_to': None,
                'feeds_from': [],
                'bracket_type': 'losers',
                'drop_in_from': 'WR1'  # Indicates losers from Winners R1
            })

        losers_rounds.append({
            'round_number': 1,
            'round_name': 'Losers Round 1',
            'round_code': 'LR1',
            'matches': lr1_matches,
            'status': 'pending'
        })
        losers_match_counter += num_lr1_matches

    # Generate remaining losers rounds
    # Pattern: After each Winners round, we have 2 Losers rounds
    # - First round: Previous losers bracket survivors only
    # - Second round: Those winners + new drop-ins from latest Winners round
    current_losers_remaining = num_lr1_matches if num_wr1_losers > 1 else 0

    for wr_idx in range(1, num_winners_rounds):
        winners_round = winners_rounds[wr_idx]
        num_wr_losers = len([m for m in winners_round['matches'] if m['competitor2'] is not None])

        if current_losers_remaining == 0 and num_wr_losers == 0:
            break

        # Losers round A: Survivors from previous losers round play each other
        if current_losers_remaining > 1:
            lr_matches = []
            num_matches = current_losers_remaining // 2
            lr_num = len(losers_rounds) + 1

            for match_num in range(1, num_matches + 1):
                lr_matches.append({
                    'match_id': f"LR{lr_num}-M{match_num}",
                    'match_number': match_num,
                    'competitor1': None,  # TBD from previous LR
                    'competitor2': None,  # TBD from previous LR
                    'seed1': None,
                    'seed2': None,
                    'winner': None,
                    'loser': None,
                    'time1': None,
                    'time2': None,
                    'finish_position1': None,
                    'finish_position2': None,
                    'status': 'pending',
                    'advances_to': None,
                    'feeds_from': [],
                    'bracket_type': 'losers',
                    'drop_in_from': None
                })

            losers_rounds.append({
                'round_number': lr_num,
                'round_name': f'Losers Round {lr_num}',
                'round_code': f'LR{lr_num}',
                'matches': lr_matches,
                'status': 'pending'
            })

            current_losers_remaining = num_matches

        # Losers round B: LR winners + Winners round losers
        if current_losers_remaining > 0 and num_wr_losers > 0:
            lr_matches = []
            num_matches = current_losers_remaining  # Should equal num_wr_losers
            lr_num = len(losers_rounds) + 1

            for match_num in range(1, num_matches + 1):
                lr_matches.append({
                    'match_id': f"LR{lr_num}-M{match_num}",
                    'match_number': match_num,
                    'competitor1': None,  # TBD from previous LR
                    'competitor2': None,  # TBD from Winners round drop-in
                    'seed1': None,
                    'seed2': None,
                    'winner': None,
                    'loser': None,
                    'time1': None,
                    'time2': None,
                    'finish_position1': None,
                    'finish_position2': None,
                    'status': 'pending',
                    'advances_to': None,
                    'feeds_from': [],
                    'bracket_type': 'losers',
                    'drop_in_from': f'WR{wr_idx + 1}'
                })

            losers_rounds.append({
                'round_number': lr_num,
                'round_name': f'Losers Round {lr_num}',
                'round_code': f'LR{lr_num}',
                'matches': lr_matches,
                'status': 'pending'
            })

            current_losers_remaining = num_matches

    return losers_rounds


def create_grand_finals_match() -> Dict:
    """Create the grand finals match structure.

    Returns:
        dict: Grand finals match object
    """
    return {
        'match_id': 'GF-M1',
        'match_number': 1,
        'competitor1': None,  # TBD: Winners bracket winner
        'competitor2': None,  # TBD: Losers bracket winner
        'seed1': None,
        'seed2': None,
        'winner': None,
        'loser': None,
        'time1': None,
        'time2': None,
        'finish_position1': None,
        'finish_position2': None,
        'status': 'pending',
        'advances_to': None,
        'feeds_from': [],
        'bracket_type': 'grand_finals'
    }


# ===========================================================================
# SEEDING & PREDICTIONS
# ===========================================================================

def generate_bracket_seeds(
    competitors_df: pd.DataFrame,
    wood_species: str,
    wood_diameter: float,
    wood_quality: int,
    event_code: str
) -> Dict[str, Dict]:
    """Generate predictions for all competitors and assign seeds.

    Seed 1 = fastest predicted time (best competitor)
    Seed N = slowest predicted time (weakest competitor)

    Args:
        competitors_df: DataFrame with competitor info
        wood_species: Wood species code
        wood_diameter: Diameter in mm
        wood_quality: Quality rating 1-10
        event_code: 'SB' or 'UH'

    Returns:
        dict: {competitor_name: prediction_with_seed}
    """
    from woodchopping.predictions.prediction_aggregator import (
        get_all_predictions,
        select_best_prediction
    )
    from woodchopping.data import load_results_df

    results_df = load_results_df()
    predictions = {}

    # Get predictions for all competitors
    for _, comp_row in competitors_df.iterrows():
        comp_name = comp_row['competitor_name']

        # Get all prediction methods
        all_preds = get_all_predictions(
            comp_name,
            wood_species,
            wood_diameter,
            wood_quality,
            event_code,
            results_df,
            tournament_results=None  # No prior tournament data
        )

        # Select best prediction
        pred_time, pred_method, pred_conf, pred_exp = select_best_prediction(all_preds)

        predictions[comp_name] = {
            'predicted_time': pred_time,
            'method_used': pred_method,
            'confidence': pred_conf,
            'explanation': pred_exp,
            'predictions': all_preds  # Store all for reference
        }

    # Sort by predicted time (fastest first)
    sorted_competitors = sorted(
        predictions.items(),
        key=lambda x: x[1]['predicted_time']
    )

    # Assign seeds (1 = fastest)
    for seed, (comp_name, pred_data) in enumerate(sorted_competitors, 1):
        predictions[comp_name]['seed'] = seed

    return predictions


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

def find_match_by_id(bracket_state: Dict, match_id: str) -> Optional[Dict]:
    """Find a match by its ID."""
    for round_obj in bracket_state['rounds']:
        for match in round_obj['matches']:
            if match['match_id'] == match_id:
                return match
    return None


def get_current_match(bracket_state: Dict) -> Optional[Dict]:
    """Get the current pending match that needs result entry.

    For single elimination: searches rounds
    For double elimination: searches winners_rounds, losers_rounds, then grand_finals
    """
    # Double elimination
    if bracket_state.get('elimination_type') == 'double':
        # Check winners bracket first
        if 'winners_rounds' in bracket_state:
            for round_obj in bracket_state['winners_rounds']:
                for match in round_obj['matches']:
                    if match['status'] in ['pending', 'in_progress'] and match['status'] != 'bye':
                        if match['competitor1'] and match['competitor2']:
                            return match

        # Check losers bracket
        if 'losers_rounds' in bracket_state:
            for round_obj in bracket_state['losers_rounds']:
                for match in round_obj['matches']:
                    if match['status'] in ['pending', 'in_progress'] and match['status'] != 'bye':
                        if match['competitor1'] and match['competitor2']:
                            return match

        # Check grand finals
        if 'grand_finals' in bracket_state:
            gf = bracket_state['grand_finals']
            if gf['status'] == 'pending' and gf['competitor1'] and gf['competitor2']:
                return gf

        return None  # Tournament complete

    # Single elimination
    current_round = bracket_state.get('current_round_number', 1)

    for round_obj in bracket_state['rounds']:
        if round_obj['round_number'] == current_round:
            for match in round_obj['matches']:
                if match['status'] in ['pending', 'in_progress'] and match['status'] != 'bye':
                    return match

    # No matches in current round - check next round
    for round_obj in bracket_state['rounds']:
        if round_obj['round_number'] > current_round:
            for match in round_obj['matches']:
                if match['status'] == 'pending' and match['competitor1'] and match['competitor2']:
                    return match

    return None  # Tournament complete


def get_competitor_seed(bracket_state: Dict, competitor_name: str) -> Optional[int]:
    """Get seed number for a competitor."""
    predictions = bracket_state.get('predictions', {})
    if competitor_name in predictions:
        return predictions[competitor_name].get('seed')
    return None


# ===========================================================================
# INITIALIZATION
# ===========================================================================

def initialize_bracket_tournament(num_stands: int, tentative_competitors: int) -> Dict:
    """Initialize new bracket tournament state.

    Args:
        num_stands: Should be 2 for bracket mode
        tentative_competitors: Estimate (not used for bracket capacity)

    Returns:
        Initialized bracket_state dict
    """
    return {
        'mode': 'bracket',
        'event_name': None,
        'event_code': None,
        'wood_species': None,
        'wood_diameter': None,
        'wood_quality': None,
        'all_competitors': [],
        'all_competitors_df': pd.DataFrame(),
        'num_competitors': 0,
        'predictions': {},
        'rounds': [],
        'current_round_number': 1,
        'current_match_index': 0,
        'total_rounds': 0,
        'completed_matches': 0,
        'total_matches': 0,
        'champion': None,
        'runner_up': None,
        'third_place': None,
        'view_only': True  # NEVER save to Excel
    }


# ===========================================================================
# MATCH RESULT ENTRY & ADVANCEMENT
# ===========================================================================

def record_match_result(
    bracket_state: Dict,
    match_id: str,
    competitor1_time: float,
    competitor2_time: float,
    finish_position1: int,
    finish_position2: int
) -> Dict:
    """Record result for a match and auto-advance winner.

    Args:
        bracket_state: Complete bracket state
        match_id: Match identifier (e.g., 'R16-M3')
        competitor1_time: Cutting time for competitor 1
        competitor2_time: Cutting time for competitor 2
        finish_position1: 1 or 2 (who finished first in real-time)
        finish_position2: 1 or 2

    Returns:
        Updated bracket_state
    """
    # Find match
    match = find_match_by_id(bracket_state, match_id)

    if not match:
        raise ValueError(f"Match {match_id} not found")

    if match['status'] == 'completed':
        raise ValueError(f"Match {match_id} already completed")

    # Update match data
    match['time1'] = competitor1_time
    match['time2'] = competitor2_time
    match['finish_position1'] = finish_position1
    match['finish_position2'] = finish_position2

    # Determine winner (finish_position 1 wins)
    if finish_position1 == 1:
        match['winner'] = match['competitor1']
        match['loser'] = match['competitor2']
    else:
        match['winner'] = match['competitor2']
        match['loser'] = match['competitor1']

    match['status'] = 'completed'

    # Auto-advance winner to next round
    if match['advances_to']:
        advance_winner_to_next_match(bracket_state, match)

    # Update bracket progress tracking
    update_bracket_progress(bracket_state)

    return bracket_state


def advance_winner_to_next_match(bracket_state: Dict, completed_match: Dict) -> None:
    """Advance match winner to next round (mutates bracket_state).

    Args:
        bracket_state: Complete bracket state
        completed_match: Just-completed match with winner
    """
    next_match_id = completed_match['advances_to']
    next_match = find_match_by_id(bracket_state, next_match_id)

    if not next_match:
        return  # Final match has no next match

    # Determine which slot in next match (based on match pairing)
    # Even-numbered matches feed top slot, odd feed bottom
    if completed_match['match_number'] % 2 == 1:
        # Odd match -> top slot
        next_match['competitor1'] = completed_match['winner']
        next_match['seed1'] = get_competitor_seed(bracket_state, completed_match['winner'])
    else:
        # Even match -> bottom slot
        next_match['competitor2'] = completed_match['winner']
        next_match['seed2'] = get_competitor_seed(bracket_state, completed_match['winner'])

    # Check if next match is ready (both competitors assigned)
    if next_match['competitor1'] and next_match['competitor2']:
        next_match['status'] = 'pending'


def update_bracket_progress(bracket_state: Dict) -> None:
    """Update bracket completion tracking (mutates bracket_state)."""
    total_completed = 0

    for round_obj in bracket_state['rounds']:
        completed_in_round = len([m for m in round_obj['matches']
                                  if m['status'] == 'completed' or m['status'] == 'bye'])
        total_completed += completed_in_round

        # Update round status
        if completed_in_round == len(round_obj['matches']):
            round_obj['status'] = 'completed'
        elif completed_in_round > 0:
            round_obj['status'] = 'in_progress'

    bracket_state['completed_matches'] = total_completed

    # Update current round/match pointers
    for round_obj in bracket_state['rounds']:
        if round_obj['status'] != 'completed':
            bracket_state['current_round_number'] = round_obj['round_number']

            # Find first incomplete match in this round
            for idx, match in enumerate(round_obj['matches']):
                if match['status'] in ['pending', 'in_progress'] and match['status'] != 'bye':
                    bracket_state['current_match_index'] = idx
                    break
            break

    # Check for tournament completion
    final_round = bracket_state['rounds'][-1]
    if final_round['status'] == 'completed':
        determine_final_placements(bracket_state)


def determine_final_placements(bracket_state: Dict) -> None:
    """Determine final placements after bracket completes.

    Champion: Final winner
    Runner-up: Final loser
    3rd place: Semi-final losers (both tied for 3rd)
    """
    final_round = bracket_state['rounds'][-1]
    final_match = final_round['matches'][0]

    bracket_state['champion'] = final_match['winner']
    bracket_state['runner_up'] = final_match['loser']

    # Find semi-final losers for 3rd place
    if len(bracket_state['rounds']) >= 2:
        semi_round = bracket_state['rounds'][-2]
        semi_losers = [m['loser'] for m in semi_round['matches'] if m['loser']]

        if len(semi_losers) == 2:
            # Both semi losers tie for 3rd
            bracket_state['third_place'] = f"{semi_losers[0]} / {semi_losers[1]} (tie)"
        elif len(semi_losers) == 1:
            bracket_state['third_place'] = semi_losers[0]

    # Build complete placement dictionary
    bracket_state['final_placements'] = {
        bracket_state['champion']: 1,
        bracket_state['runner_up']: 2
    }


# ===========================================================================
# DOUBLE ELIMINATION MATCH RESULT HANDLING
# ===========================================================================

def record_double_elim_match_result(
    bracket_state: Dict,
    match_id: str,
    competitor1_time: float,
    competitor2_time: float,
    finish_position1: int,
    finish_position2: int
) -> Dict:
    """Record result for a double elimination match and handle progression.

    Handles:
    - Winners bracket: Winner advances, loser drops to losers bracket
    - Losers bracket: Winner advances, loser is eliminated
    - Grand finals: Determines champion

    Args:
        bracket_state: Complete bracket state
        match_id: Match identifier
        competitor1_time: Cutting time for competitor 1
        competitor2_time: Cutting time for competitor 2
        finish_position1: 1 or 2 (who finished first)
        finish_position2: 1 or 2

    Returns:
        Updated bracket_state
    """
    # Find match in appropriate bracket
    match = find_match_in_double_elim(bracket_state, match_id)

    if not match:
        raise ValueError(f"Match {match_id} not found")

    if match['status'] == 'completed':
        raise ValueError(f"Match {match_id} already completed")

    # Update match data
    match['time1'] = competitor1_time
    match['time2'] = competitor2_time
    match['finish_position1'] = finish_position1
    match['finish_position2'] = finish_position2

    # Determine winner/loser
    if finish_position1 == 1:
        winner = match['competitor1']
        loser = match['competitor2']
    else:
        winner = match['competitor2']
        loser = match['competitor1']

    match['winner'] = winner
    match['loser'] = loser
    match['status'] = 'completed'

    bracket_type = match['bracket_type']

    if bracket_type == 'winners':
        # Winners bracket: Winner advances, loser drops to losers
        advance_winner_in_double_elim(bracket_state, match, 'winners')
        drop_loser_to_losers_bracket(bracket_state, match)

    elif bracket_type == 'losers':
        # Losers bracket: Winner advances, loser eliminated
        advance_winner_in_double_elim(bracket_state, match, 'losers')
        eliminate_competitor(bracket_state, loser)

    elif bracket_type == 'grand_finals':
        # Grand finals: Determine champion
        bracket_state['champion'] = winner
        bracket_state['runner_up'] = loser

    # Update progress
    update_double_elim_progress(bracket_state)

    return bracket_state


def find_match_in_double_elim(bracket_state: Dict, match_id: str) -> Dict:
    """Find match in winners, losers, or grand finals bracket."""
    # Check winners bracket
    if 'winners_rounds' in bracket_state:
        for round_obj in bracket_state['winners_rounds']:
            for match in round_obj['matches']:
                if match['match_id'] == match_id:
                    return match

    # Check losers bracket
    if 'losers_rounds' in bracket_state:
        for round_obj in bracket_state['losers_rounds']:
            for match in round_obj['matches']:
                if match['match_id'] == match_id:
                    return match

    # Check grand finals
    if 'grand_finals' in bracket_state:
        if bracket_state['grand_finals']['match_id'] == match_id:
            return bracket_state['grand_finals']

    return None


def advance_winner_in_double_elim(bracket_state: Dict, completed_match: Dict, bracket_type: str) -> None:
    """Advance winner to next match in double elimination bracket."""
    winner = completed_match['winner']
    next_match_id = completed_match.get('advances_to')

    if not next_match_id:
        # Check if this is the last match before grand finals
        if bracket_type == 'winners':
            # Winners bracket winner goes to grand finals
            gf = bracket_state['grand_finals']
            gf['competitor1'] = winner
            gf['seed1'] = get_competitor_seed(bracket_state, winner)
        elif bracket_type == 'losers':
            # Losers bracket winner goes to grand finals
            gf = bracket_state['grand_finals']
            gf['competitor2'] = winner
            gf['seed2'] = get_competitor_seed(bracket_state, winner)
        return

    # Find next match
    next_match = find_match_in_double_elim(bracket_state, next_match_id)

    if not next_match:
        return

    # Place winner in next match (top or bottom slot)
    if completed_match['match_number'] % 2 == 1:
        next_match['competitor1'] = winner
        next_match['seed1'] = get_competitor_seed(bracket_state, winner)
    else:
        next_match['competitor2'] = winner
        next_match['seed2'] = get_competitor_seed(bracket_state, winner)

    # Update status if both competitors assigned
    if next_match['competitor1'] and next_match['competitor2']:
        next_match['status'] = 'pending'


def drop_loser_to_losers_bracket(bracket_state: Dict, winners_match: Dict) -> None:
    """Drop loser from winners bracket into losers bracket."""
    loser = winners_match['loser']
    winners_round_code = winners_match['match_id'].split('-')[0]  # e.g., "R1" from "R1-M1"

    # Find the appropriate losers bracket match for this drop-in
    for round_obj in bracket_state['losers_rounds']:
        for match in round_obj['matches']:
            drop_in_source = match.get('drop_in_from')

            if drop_in_source and drop_in_source == winners_round_code:
                # This losers match accepts drop-ins from this winners round
                if match['competitor1'] is None:
                    match['competitor1'] = loser
                    match['seed1'] = get_competitor_seed(bracket_state, loser)
                elif match['competitor2'] is None:
                    match['competitor2'] = loser
                    match['seed2'] = get_competitor_seed(bracket_state, loser)

                # Check if match is ready
                if match['competitor1'] and match['competitor2']:
                    match['status'] = 'pending'
                return


def eliminate_competitor(bracket_state: Dict, competitor: str) -> None:
    """Mark competitor as eliminated from tournament."""
    if 'eliminated' not in bracket_state:
        bracket_state['eliminated'] = []

    if competitor not in bracket_state['eliminated']:
        bracket_state['eliminated'].append(competitor)


def update_double_elim_progress(bracket_state: Dict) -> None:
    """Update completion tracking for double elimination bracket."""
    total_completed = 0

    # Count winners bracket
    if 'winners_rounds' in bracket_state:
        for round_obj in bracket_state['winners_rounds']:
            completed = len([m for m in round_obj['matches']
                           if m['status'] in ['completed', 'bye']])
            total_completed += completed

            # Update round status
            if completed == len(round_obj['matches']):
                round_obj['status'] = 'completed'
            elif completed > 0:
                round_obj['status'] = 'in_progress'

    # Count losers bracket
    if 'losers_rounds' in bracket_state:
        for round_obj in bracket_state['losers_rounds']:
            completed = len([m for m in round_obj['matches']
                           if m['status'] in ['completed', 'bye']])
            total_completed += completed

            # Update round status
            if completed == len(round_obj['matches']):
                round_obj['status'] = 'completed'
            elif completed > 0:
                round_obj['status'] = 'in_progress'

    # Count grand finals
    if 'grand_finals' in bracket_state:
        if bracket_state['grand_finals']['status'] == 'completed':
            total_completed += 1

    bracket_state['completed_matches'] = total_completed


def enter_match_results_interactive(bracket_state: Dict) -> Dict:
    """Interactive CLI workflow for entering match results.

    Workflow:
    1. Show current match details
    2. Prompt for cutting times
    3. Prompt for finish order (who finished first)
    4. Confirm and record
    5. Display updated bracket
    6. Advance to next match or show completion

    Returns:
        Updated bracket_state
    """
    current_match = get_current_match(bracket_state)

    if not current_match:
        print("\n[OK] All matches completed! Tournament finished.")
        display_final_results(bracket_state)
        return bracket_state

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "ENTER MATCH RESULTS".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    # Display current match
    render_match_box(current_match, is_current=True)

    comp1 = current_match['competitor1']
    comp2 = current_match['competitor2']

    print(f"\n{'=' * 70}")
    print("STEP 1: ENTER CUTTING TIMES")
    print(f"{'=' * 70}")
    print("Enter the raw cutting time for each competitor (seconds)\n")

    # Get cutting times
    while True:
        try:
            time1_str = input(f"Cutting time for {comp1}: ").strip()
            time1 = float(time1_str)
            if time1 <= 0:
                print("  Time must be positive. Try again.")
                continue
            break
        except ValueError:
            print("  Invalid number. Try again.")

    while True:
        try:
            time2_str = input(f"Cutting time for {comp2}: ").strip()
            time2 = float(time2_str)
            if time2 <= 0:
                print("  Time must be positive. Try again.")
                continue
            break
        except ValueError:
            print("  Invalid number. Try again.")

    print(f"\n{'=' * 70}")
    print("STEP 2: ENTER FINISH ORDER")
    print(f"{'=' * 70}")
    print("Who finished FIRST in real-time (crossed finish line first)?\n")
    print(f"  1) {comp1} ({time1:.1f}s)")
    print(f"  2) {comp2} ({time2:.1f}s)")

    while True:
        finish_choice = input("\nWho finished first? (1 or 2): ").strip()
        if finish_choice in ['1', '2']:
            break
        print("  Invalid choice. Enter 1 or 2.")

    if finish_choice == '1':
        finish_pos1 = 1
        finish_pos2 = 2
        winner = comp1
    else:
        finish_pos1 = 2
        finish_pos2 = 1
        winner = comp2

    # Confirmation
    print(f"\n{'=' * 70}")
    print("CONFIRM RESULTS:")
    print(f"{'=' * 70}")
    print(f"  {comp1}: {time1:.1f}s - Finished {'1st' if finish_pos1 == 1 else '2nd'}")
    print(f"  {comp2}: {time2:.1f}s - Finished {'1st' if finish_pos2 == 1 else '2nd'}")
    print(f"\n  WINNER: {winner}")

    confirm = input("\nConfirm these results? (y/n): ").strip().lower()

    if confirm != 'y':
        print("\n⚠️ Results cancelled. Re-enter match results.")
        return bracket_state

    # Record results (use appropriate function based on elimination type)
    if bracket_state.get('elimination_type') == 'double':
        bracket_state = record_double_elim_match_result(
            bracket_state,
            current_match['match_id'],
            time1,
            time2,
            finish_pos1,
            finish_pos2
        )
    else:
        bracket_state = record_match_result(
            bracket_state,
            current_match['match_id'],
            time1,
            time2,
            finish_pos1,
            finish_pos2
        )

    print(f"\n[OK] Results recorded for {current_match['match_id']}")

    # Display advancement message
    if bracket_state.get('elimination_type') == 'double':
        bracket_type = current_match.get('bracket_type', 'winners')
        loser = comp1 if winner == comp2 else comp2

        if bracket_type == 'winners':
            print(f"[OK] {winner} advances in Winners Bracket")
            print(f"  {loser} drops to Losers Bracket")
        elif bracket_type == 'losers':
            print(f"[OK] {winner} advances in Losers Bracket")
            print(f"? {loser} is ELIMINATED")
        elif bracket_type == 'grand_finals':
            print(f"[OK] {winner} is the CHAMPION!")
            print(f"  {loser} is Runner-Up")
    else:
        if current_match.get('advances_to'):
            print(f"[OK] {winner} advances to {current_match['advances_to']}")

    return bracket_state


def sequential_match_entry_workflow(bracket_state: Dict) -> Dict:
    """Complete workflow for entering all bracket results sequentially.

    Continues until all matches completed or user exits.
    """
    while True:
        current_match = get_current_match(bracket_state)

        if not current_match:
            print("\n[OK] Tournament complete!")
            display_final_results(bracket_state)
            break

        print(f"\n{'=' * 70}")
        print(f"Current Progress: {bracket_state['completed_matches']}/{bracket_state['total_matches']} matches")
        print(f"{'=' * 70}")

        # Enter results for current match
        bracket_state = enter_match_results_interactive(bracket_state)

        # Ask to continue
        print("\n" + "=" * 70)
        choice = input("Options: [1] Next Match  [2] View Bracket  [3] Exit: ").strip()

        if choice == '2':
            if bracket_state.get('elimination_type') == 'double':
                render_double_elim_bracket_ascii(bracket_state)
            else:
                render_bracket_tree_ascii(bracket_state)
        elif choice == '3':
            print("\nExiting match entry. Progress saved.")
            break

    return bracket_state


# ===========================================================================
# VISUAL DISPLAY - MATCH BOX RENDERING
# ===========================================================================

def render_match_box(match: Dict, is_current: bool = False) -> None:
    """Render a single match with box-drawing characters.

    Args:
        match: Match dict
        is_current: Whether this is the current active match (highlight)
    """
    # Highlight current match
    if is_current:
        top_char = "?"
        bottom_char = "?"
        side_char = "?"
        mid_char = "?"
        horizontal = "?"
    else:
        top_char = "+"
        bottom_char = "+"
        side_char = "|"
        mid_char = "+"
        horizontal = "-"

    width = 60

    # Status indicator
    if match['status'] == 'completed':
        status = "[OK]"
    elif match['status'] == 'in_progress':
        status = "? ACTIVE"
    elif match['status'] == 'bye':
        status = "BYE"
    else:
        status = "PENDING"

    # Top border
    print(f"{top_char}{horizontal * (width - 2)}{top_char.replace('?', '?').replace('+', '+')}")

    # Match header
    header = f" {match['match_id']}"
    padding = width - len(header) - len(status) - 4
    print(f"{side_char}{header}{' ' * padding}[{status}]{side_char}")

    # Middle border
    print(f"{mid_char}{horizontal * (width - 2)}{mid_char.replace('?', '?').replace('+', '+')}")

    # Competitor 1
    if match['competitor1']:
        comp1_line = format_competitor_line(
            match['competitor1'],
            match['seed1'],
            match['time1'],
            match['finish_position1'],
            match['winner']
        )
        print(f"{side_char} {comp1_line:<{width - 3}}{side_char}")
    else:
        print(f"{side_char} {'TBD':<{width - 3}}{side_char}")

    # Competitor 2
    if match['competitor2']:
        comp2_line = format_competitor_line(
            match['competitor2'],
            match['seed2'],
            match['time2'],
            match['finish_position2'],
            match['winner']
        )
        print(f"{side_char} {comp2_line:<{width - 3}}{side_char}")
    elif match['status'] == 'bye':
        print(f"{side_char} {'(Bye - auto-advance)':<{width - 3}}{side_char}")
    else:
        print(f"{side_char} {'TBD':<{width - 3}}{side_char}")

    # Winner line (if match completed)
    if match['winner']:
        print(f"{mid_char}{horizontal * (width - 2)}{mid_char.replace('?', '?').replace('+', '+')}")
        advances_text = f"-> Advances to {match['advances_to']}" if match.get('advances_to') else "-> CHAMPION!"
        winner_line = f"Winner: {match['winner']} {advances_text}"
        print(f"{side_char} {winner_line:<{width - 3}}{side_char}")

    # Bottom border
    print(f"{bottom_char}{horizontal * (width - 2)}{bottom_char.replace('?', '?').replace('+', '+')}")
    print()


def format_competitor_line(
    name: str,
    seed: Optional[int],
    time: Optional[float],
    finish_pos: Optional[int],
    winner: Optional[str]
) -> str:
    """Format a competitor line for match display.

    Returns:
        Formatted string like: "(1) John Smith         23.5s  [1st] [OK]"
    """
    # Seed and name
    seed_str = f"({seed})" if seed else "   "
    name_trunc = name[:25] if name else "TBD"

    # Time
    time_str = f"{time:5.1f}s" if time else "  ---  "

    # Finish position
    if finish_pos == 1:
        pos_str = "[1st]"
    elif finish_pos == 2:
        pos_str = "[2nd]"
    else:
        pos_str = "     "

    # Winner indicator
    winner_mark = "[OK]" if name == winner else " "

    return f"{seed_str} {name_trunc:<27} {time_str}  {pos_str} {winner_mark}"


def display_final_results(bracket_state: Dict) -> None:
    """Display final tournament results."""
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "🏆 TOURNAMENT COMPLETE! 🏆".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    print("🏆 FINAL RESULTS:")
    print("=" * 70)
    print(f"\n  1st Place:  {bracket_state.get('champion', 'N/A')}")
    print(f"  2nd Place:  {bracket_state.get('runner_up', 'N/A')}")
    print(f"  3rd Place:  {bracket_state.get('third_place', 'N/A')}")
    print()


# ===========================================================================
# VISUAL DISPLAY - ASCII TREE RENDERING
# ===========================================================================

def render_bracket_tree_ascii(bracket_state: Dict) -> None:
    """Render horizontal bracket tree with ASCII art.

    For small brackets (<=16 competitors), shows full tree.
    For larger brackets, shows current round section.
    """
    print("\n╔" + "═" * 68 + "╗")
    print("║" + f"  {bracket_state['event_name']}".center(68) + "║")
    print("║" + "  HEAD-TO-HEAD BRACKET".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    num_competitors = bracket_state['num_competitors']

    if num_competitors <= 16:
        # Show full bracket tree
        render_full_bracket_tree(bracket_state)
    else:
        # Show current round section for large brackets
        print("(Large bracket - showing round-by-round view)\n")
        render_round_section(bracket_state, bracket_state['current_round_number'])


def render_double_elim_bracket_ascii(bracket_state: Dict) -> None:
    """Render double elimination bracket with winners, losers, and grand finals.

    Layout:
    - Winners Bracket section
    - Losers Bracket section
    - Grand Finals section
    """
    print("\n╔" + "═" * 68 + "╗")
    print("║" + f"  {bracket_state['event_name']}".center(68) + "║")
    print("║" + "  DOUBLE ELIMINATION BRACKET".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    # WINNERS BRACKET
    print("╔" + "═" * 68 + "╗")
    print("║" + "  WINNERS BRACKET".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if 'winners_rounds' in bracket_state:
        for round_obj in bracket_state['winners_rounds']:
            print(f"\n{round_obj['round_name']}:")
            print("-" * 70)
            for match in round_obj['matches']:
                render_match_box_compact(match)
                print()

    # LOSERS BRACKET
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "  LOSERS BRACKET".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    if 'losers_rounds' in bracket_state:
        for round_obj in bracket_state['losers_rounds']:
            print(f"\n{round_obj['round_name']}:")
            print("-" * 70)
            for match in round_obj['matches']:
                render_match_box_compact(match)
                if match.get('drop_in_from'):
                    print(f"  ↓ Drop-ins from {match['drop_in_from']}")
                print()

    # GRAND FINALS
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "  GRAND FINALS".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    if 'grand_finals' in bracket_state:
        render_match_box_compact(bracket_state['grand_finals'])

    # Show eliminated competitors
    if bracket_state.get('eliminated'):
        print("\n╔" + "═" * 68 + "╗")
        print("║" + "  ELIMINATED".center(68) + "║")
        print("╚" + "═" * 68 + "╝")
        for competitor in bracket_state['eliminated']:
            print(f"  ✗ {competitor}")


def render_match_box_compact(match: Dict) -> None:
    """Render a compact match box for double elimination display."""
    match_id = match['match_id']
    status = match['status']

    comp1 = match.get('competitor1', 'TBD')
    comp2 = match.get('competitor2', 'TBD')
    seed1 = match.get('seed1', '')
    seed2 = match.get('seed2', '')
    time1 = match.get('time1')
    time2 = match.get('time2')
    winner = match.get('winner')

    # Format competitor names with seeds
    c1_display = f"{comp1} (#{seed1})" if seed1 else comp1
    c2_display = f"{comp2} (#{seed2})" if seed2 else comp2

    # Truncate long names
    c1_display = c1_display[:28]
    c2_display = c2_display[:28]

    # Status indicators
    if status == 'completed':
        w1 = "[OK]" if winner == comp1 else " "
        w2 = "[OK]" if winner == comp2 else " "
        print(f"  {match_id}: {w1} {c1_display:30} {time1:5.2f}s" if time1 else f"  {match_id}: {w1} {c1_display:30}")
        print(f"         {w2} {c2_display:30} {time2:5.2f}s" if time2 else f"         {w2} {c2_display:30}")
    elif status == 'bye':
        print(f"  {match_id}: [OK] {c1_display:30} (BYE)")
    elif status == 'pending' and comp1 != 'TBD' and comp2 != 'TBD':
        print(f"  {match_id}:   {c1_display:30} [Ready]")
        print(f"           {c2_display:30}")
    else:
        print(f"  {match_id}:   {c1_display:30} [TBD]")
        print(f"           {c2_display:30}")


def render_full_bracket_tree(bracket_state: Dict) -> None:
    """Render complete bracket tree with connecting lines."""
    rounds = bracket_state['rounds']

    # Print round headers
    round_headers = []
    for round_obj in rounds:
        round_headers.append(round_obj['round_name'])

    # Calculate column widths
    col_width = 22
    spacing = "   "

    # Print headers
    header_line = ""
    for header in round_headers:
        header_line += header[:col_width-2].ljust(col_width) + spacing
    print(header_line)
    print("-" * len(header_line))
    print()

    # Simple tree representation - vertical stacking with connections
    # For each match in Round 1, print vertically with connections to next round
    render_tree_recursive(rounds, 0, 0, col_width, spacing)

    print()
    print("Legend: [OK] = Winner  +++ = Bracket connections  ? = Advances")
    print()


def render_tree_recursive(rounds: List[Dict], round_idx: int, match_idx: int, col_width: int, spacing: str) -> None:
    """Recursively render bracket tree (simplified vertical display)."""
    if round_idx >= len(rounds):
        return

    round_obj = rounds[round_idx]

    for idx, match in enumerate(round_obj['matches']):
        # Format competitor names with seeds and winner marks
        comp1 = f"({match['seed1']}) {match['competitor1']}" if match['competitor1'] else "TBD"
        comp2 = f"({match['seed2']}) {match['competitor2']}" if match['competitor2'] and match['status'] != 'bye' else "(Bye)" if match['status'] == 'bye' else "TBD"

        # Add winner mark
        if match['winner']:
            if match['winner'] == match['competitor1']:
                comp1 += " [OK]"
            elif match['winner'] == match['competitor2']:
                comp2 += " [OK]"

        # Truncate to fit
        comp1 = comp1[:col_width-2]
        comp2 = comp2[:col_width-2]

        # Print match
        print(f"{comp1.ljust(col_width)}  +")
        print(f"{' ' * col_width}  +--? ", end="")

        # Print advancing competitor if exists
        if match['winner']:
            adv_name = f"{match['winner'][:15]} [OK]"
            print(adv_name)
        else:
            print("TBD")

        print(f"{comp2.ljust(col_width)}  +")
        print()


def render_round_section(bracket_state: Dict, round_number: int) -> None:
    """Render a specific round with detailed match boxes."""
    rounds = bracket_state['rounds']

    for round_obj in rounds:
        if round_obj['round_number'] == round_number:
            print(f"\n{'?' * 70}")
            print(f"  {round_obj['round_name'].upper()} ({round_obj['round_code']})")
            print(f"{'?' * 70}")

            current_match = get_current_match(bracket_state)

            for match in round_obj['matches']:
                is_current = (current_match and match['match_id'] == current_match['match_id'])
                render_match_box(match, is_current=is_current)

            print()
            break


# ===========================================================================
# HTML EXPORT
# ===========================================================================

def export_bracket_to_html(bracket_state: Dict) -> str:
    """Generate HTML file with bracket visualization.

    Args:
        bracket_state: Complete bracket state

    Returns:
        Path to generated HTML file
    """
    html_content = generate_bracket_html_structure(bracket_state)

    # Save to file
    event_name_safe = bracket_state['event_name'].replace(' ', '_').replace('/', '-')
    filename = f"bracket_{event_name_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return filepath


def open_bracket_in_browser(filepath: str) -> None:
    """Open HTML file in default browser."""
    webbrowser.open(f'file://{os.path.abspath(filepath)}')


def generate_bracket_html_structure(bracket_state: Dict) -> str:
    """Generate complete HTML document with bracket."""
    css = generate_bracket_css()
    bracket_html = generate_bracket_rounds_html(bracket_state['rounds'])

    wood_info = f"{bracket_state['wood_species']} | {bracket_state['wood_diameter']}mm | Quality: {bracket_state['wood_quality']}/10"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{bracket_state['event_name']} - Tournament Bracket</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{bracket_state['event_name']}</h1>
            <p class="subtitle">Head-to-Head Championship Bracket</p>
            <p class="info">Wood: {wood_info}</p>
            <p class="stats">Competitors: {bracket_state['num_competitors']} | Rounds: {bracket_state['total_rounds']} | Matches Completed: {bracket_state['completed_matches']}/{bracket_state['total_matches']}</p>
        </header>

        <div class="bracket-container">
            {bracket_html}
        </div>

        <footer>
            <p>Generated by STRATHEX Woodchopping Handicap System</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>"""

    return html


def generate_bracket_css() -> str:
    """Generate CSS styles for bracket HTML."""
    return """
        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }

        header {
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        h1 {
            margin: 0;
            color: #333;
            font-size: 2.5em;
        }

        .subtitle {
            color: #666;
            font-size: 1.2em;
            margin: 5px 0;
        }

        .info {
            color: #888;
            font-size: 1em;
            margin: 5px 0;
        }

        .stats {
            color: #555;
            font-weight: bold;
            margin: 10px 0 0 0;
        }

        .bracket-container {
            display: flex;
            flex-direction: row;
            gap: 40px;
            overflow-x: auto;
            padding: 20px 0;
        }

        .round {
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            min-width: 250px;
        }

        .round-header {
            text-align: center;
            font-weight: bold;
            font-size: 1.2em;
            color: #667eea;
            margin-bottom: 20px;
            padding: 10px;
            background: #f0f0f0;
            border-radius: 5px;
        }

        .match {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            background: white;
            transition: all 0.3s ease;
        }

        .match:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }

        .match.completed {
            background: #d4edda;
            border-color: #28a745;
        }

        .match.active {
            background: #fff3cd;
            border-color: #ffc107;
            box-shadow: 0 0 10px rgba(255, 193, 7, 0.5);
        }

        .match.bye {
            background: #e9ecef;
            border-color: #6c757d;
            border-style: dashed;
        }

        .match-header {
            font-weight: bold;
            color: #555;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .match-id {
            font-size: 0.9em;
        }

        .match-status {
            font-size: 0.85em;
            padding: 3px 8px;
            border-radius: 12px;
            background: #f0f0f0;
        }

        .match.completed .match-status {
            background: #28a745;
            color: white;
        }

        .match.active .match-status {
            background: #ffc107;
            color: #333;
        }

        .competitor {
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .competitor.winner {
            font-weight: bold;
            background: #c3e6cb;
            border-left: 4px solid #28a745;
        }

        .comp-name {
            flex-grow: 1;
        }

        .seed {
            color: #666;
            font-size: 0.9em;
            margin-right: 8px;
        }

        .time {
            color: #555;
            font-family: monospace;
            margin-left: 10px;
        }

        .winner-indicator {
            color: #28a745;
            font-size: 1.2em;
            margin-left: 5px;
        }

        .match-result {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #f0f0f0;
            color: #888;
            font-size: 0.9em;
        }

        @media print {
            body {
                background: white;
            }
            .container {
                box-shadow: none;
            }
        }
    """


def generate_bracket_rounds_html(rounds: List[Dict]) -> str:
    """Generate HTML for all bracket rounds."""
    rounds_html = ""

    for round_obj in rounds:
        round_html = f"""
        <div class="round">
            <div class="round-header">{round_obj['round_name']}</div>
            {generate_matches_html(round_obj['matches'])}
        </div>
        """
        rounds_html += round_html

    return rounds_html


def generate_matches_html(matches: List[Dict]) -> str:
    """Generate HTML for matches in a round."""
    matches_html = ""

    for match in matches:
        status_class = match['status']
        status_text = {
            'completed': '[OK] Complete',
            'in_progress': '? Active',
            'pending': 'Pending',
            'bye': 'BYE'
        }.get(match['status'], 'Pending')

        # Competitor 1
        comp1_html = generate_competitor_html(
            match['competitor1'],
            match['seed1'],
            match['time1'],
            match['finish_position1'],
            match['winner']
        ) if match['competitor1'] else '<div class="competitor">TBD</div>'

        # Competitor 2
        if match['status'] == 'bye':
            comp2_html = '<div class="competitor">(Bye - auto-advance)</div>'
        elif match['competitor2']:
            comp2_html = generate_competitor_html(
                match['competitor2'],
                match['seed2'],
                match['time2'],
                match['finish_position2'],
                match['winner']
            )
        else:
            comp2_html = '<div class="competitor">TBD</div>'

        # Match result footer
        result_html = ""
        if match['winner']:
            advances_text = f"Advances to {match['advances_to']}" if match.get('advances_to') else "CHAMPION!"
            result_html = f'<div class="match-result">Winner: {match["winner"]} -> {advances_text}</div>'

        match_html = f"""
        <div class="match {status_class}">
            <div class="match-header">
                <span class="match-id">{match['match_id']}</span>
                <span class="match-status">{status_text}</span>
            </div>
            {comp1_html}
            {comp2_html}
            {result_html}
        </div>
        """

        matches_html += match_html

    return matches_html


def generate_competitor_html(
    name: str,
    seed: Optional[int],
    time: Optional[float],
    finish_pos: Optional[int],
    winner: Optional[str]
) -> str:
    """Generate HTML for a single competitor."""
    is_winner = (name == winner)
    winner_class = "winner" if is_winner else ""
    winner_mark = '<span class="winner-indicator">[OK]</span>' if is_winner else ""

    seed_html = f'<span class="seed">({seed})</span>' if seed else ''
    time_html = f'<span class="time">{time:.1f}s</span>' if time else ''
    pos_html = f'<span class="time">[{"1st" if finish_pos == 1 else "2nd" if finish_pos == 2 else ""}]</span>' if finish_pos else ''

    return f"""
    <div class="competitor {winner_class}">
        <span class="comp-name">{seed_html}{name}</span>
        {time_html}
        {pos_html}
        {winner_mark}
    </div>
    """
