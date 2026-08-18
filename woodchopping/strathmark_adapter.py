# -*- coding: utf-8 -*-
"""
STRATHEX <-> STRATHMARK adapter.

This module is the single production boundary between STRATHEX's DataFrame-
based tournament application and STRATHMARK's typed prediction engine.  It
translates records, executes the prediction stack, delegates mark arithmetic,
and exposes small compatibility facades for persistence and simulation.

No tournament workflow or user-interface policy belongs here.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Mapping, Optional

import pandas as pd
import strathmark.variance as _sm_variance
from strathmark import (
    CompetitorRecord,
    HandicapCalculator,
    HistoricalResult,
    PredictionResult,
    ResultStore,
    WoodProfile,
    get_all_predictions,
    select_best_prediction,
)
from strathmark.config import llm_config
from strathmark.fairness import (
    get_ai_assessment_of_handicaps as _sm_assess_handicaps,
)
from strathmark.fairness import (
    get_championship_race_analysis as _sm_championship_analysis,
)
from strathmark.fairness import (
    simulate_and_assess_handicaps as _sm_simulate_and_assess,
)
from strathmark.predictor import MLModel

_log = logging.getLogger(__name__)
_ML_MODEL_CACHE: Dict[tuple, Optional[MLModel]] = {}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _name_key(value: Any) -> str:
    """Return a stable, case-insensitive key for a competitor name."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _clean_gender(value: Any) -> Optional[str]:
    """Normalise roster gender values to STRATHMARK's ``M`` / ``F`` encoding."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text in {"M", "MALE", "MEN", "MAN"}:
        return "M"
    if text in {"F", "FEMALE", "WOMEN", "WOMAN"}:
        return "F"
    return None


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def prepare_results_for_strathmark(
    results_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Return a unique-column DataFrame safe for the pinned engine boundary.

    STRATHEX's loaded Results frame legitimately carries both ``competitor_id``
    and the mapped ``competitor_name``. STRATHMARK 0.4.1 treats both as aliases
    for ``competitor_name`` during normalization; passing both creates duplicate
    columns and makes ``df["competitor_name"]`` a DataFrame instead of a Series.

    Only colliding alias families are rewritten. Frames that are already safe
    are returned unchanged so existing cache and caller identity semantics remain
    intact. Canonical values win; aliases fill only missing cells.
    """
    if results_df is None or not isinstance(results_df, pd.DataFrame):
        return pd.DataFrame()
    if results_df.empty:
        return results_df

    normalized_names = [str(column).strip().lower() for column in results_df.columns]
    alias_groups = {
        "competitor_name": (
            "competitor_name",
            "competitor name",
            "competitorname",
            "name",
            "competitor_id",
            "competitorid",
        ),
        "event": ("event", "event_code", "eventcode"),
        "raw_time": (
            "raw_time",
            "actual_time",
            "actualtime",
            "time",
            "time (seconds)",
            "time(seconds)",
        ),
        "size_mm": (
            "size_mm",
            "diameter_mm",
            "diameter",
            "size",
            "size (mm)",
            "size(mm)",
        ),
        "species": (
            "species",
            "wood_species",
            "woodspecies",
            "species code",
            "speciescode",
        ),
        "result_date": (
            "result_date",
            "result date",
            "date",
            "date (optional)",
        ),
    }

    collisions: Dict[str, List[int]] = {}
    for target, aliases in alias_groups.items():
        positions = [
            position
            for alias in aliases
            for position, name in enumerate(normalized_names)
            if name == alias
        ]
        if len(positions) > 1:
            collisions[target] = positions

    if not collisions and results_df.columns.is_unique:
        return results_df

    consumed_positions = {
        position for positions in collisions.values() for position in positions
    }
    output = pd.DataFrame(index=results_df.index)

    for position, column_name in enumerate(results_df.columns):
        if position in consumed_positions:
            continue
        normalized = str(column_name).strip().lower()
        if normalized not in output.columns:
            output[normalized] = results_df.iloc[:, position]

    for target, positions in collisions.items():
        combined = results_df.iloc[:, positions[0]].copy()
        for position in positions[1:]:
            candidate = results_df.iloc[:, position]
            missing = combined.isna()
            if combined.dtype == object:
                missing = missing | combined.astype(str).str.strip().eq("")
            combined = combined.where(~missing, candidate)
        output[target] = combined

    return output


def enrich_results_with_roster(
    results_df: Optional[pd.DataFrame],
    roster_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Fill historical-result gender values from the competitor roster.

    STRATHMARK's ML feature schema includes gender.  The Results sheet stores
    performance observations while the Competitor sheet stores gender, so the
    two sources must be joined before model training.  Existing valid result
    values are preserved and the input DataFrames are never mutated.
    """
    results = results_df.copy() if isinstance(results_df, pd.DataFrame) else pd.DataFrame()
    if results.empty or roster_df is None or roster_df.empty:
        return results

    roster = roster_df.copy()
    roster.columns = [str(col).strip() for col in roster.columns]
    roster.rename(
        columns={
            "Name": "competitor_name",
            "name": "competitor_name",
            "Competitor Name": "competitor_name",
            "Gender": "gender",
        },
        inplace=True,
    )

    if "competitor_name" not in results.columns or not {
        "competitor_name",
        "gender",
    }.issubset(roster.columns):
        return results

    gender_by_name: Dict[str, str] = {}
    for _, row in roster[["competitor_name", "gender"]].iterrows():
        key = _name_key(row.get("competitor_name"))
        gender = _clean_gender(row.get("gender"))
        if key and gender:
            gender_by_name[key] = gender

    if not gender_by_name:
        return results

    mapped = results["competitor_name"].map(lambda value: gender_by_name.get(_name_key(value)))
    if "gender" not in results.columns:
        results["gender"] = mapped
    else:
        existing = results["gender"].map(_clean_gender)
        results["gender"] = existing.where(existing.notna(), mapped)

    return results


def build_gender_map(
    competitor_df: Optional[pd.DataFrame],
    results_df: Optional[pd.DataFrame] = None,BË ôˆdÈ8ÔÂÀ¢'F–ÖV÷WB#¢ÆÆÕö6öæf–råD”ÔTõUEõ4T4ôäE2À¢Ğ ¢&VF–7F–öç5ö'•öæÖS¢F–7E·7G"ÂF–7E·7G"Â÷F–öæÅµ&VF–7F–öå&W7VÇEÕÕÒÒ·Ğ¢6VÆV7FVEö'•öæÖS¢F–7E·7G"Â&VF–7F–öå&W7VÇEÒÒ·Ğ ¢f÷"&V6÷&B–â6ö×WF—F÷%÷&V6÷&G3 ¢G'“ ¢ÆÅ÷&VF–7F–öç2ÒvWEöÆÅ÷&VF–7F–öç2€¢&V6÷&BÀ¢vööBÀ¢WfVçEö6öFRÀ¢vööEöFFöFc×vööEöFbÀ¢&W7VÇG5öFcÖVæv–æU÷&W7VÇG2À¢ÖÅöÖöFVÃÖÖÅöÖöFVÂÀ¢ÆÆÕö6Æ–VçCÖÆÆÕö6Æ–VçBÀ¢¢W†6WBW†6WF–öâ2f—'7EöW'&÷# ¢öÆörçv&æ–ær€¢%&VF–7F–öâ6ö×&—6öâf–ÆVBf÷"W2v—F‚ÄÄÒVæ&ÆVC²&WG'––ærFWFW&Ö–æ—7F–2ÖWF†öG2öæÇ“¢W2"À¢&V6÷&BææÖRÀ¢f—'7EöW'&÷"À¢¢ÆÅ÷&VF–7F–öç2ÒvWEöÆÅ÷&VF–7F–öç2€¢&V6÷&BÀ¢vööBÀ¢WfVçEö6öFRÀ¢vööEöFFöFc×vööEöFbÀ¢&W7VÇG5öFcÖVæv–æU÷&W7VÇG2À¢ÖÅöÖöFVÃÖÖÅöÖöFVÂÀ¢ÆÆÕö6Æ–VçCÔæöæRÀ¢ ¢6VÆV7FVBÒ6VÆV7Eö&W7E÷&VF–7F–öâ†ÆÅ÷&VF–7F–öç2¢&VF–7F–öç5ö'•öæÖU·&V6÷&BææÖUÒÒÆÅ÷&VF–7F–öç0¢6VÆV7FVEö'•öæÖU·&V6÷&BææÖUÒÒ6VÆV7FV@ ¢6VÆV7FVE÷fÇVW2Ò¶æÖS¢&VF–7F–öâçfÇVRf÷"æÖRÂ&VF–7F–öâ–â6VÆV7FVEö'•öæÖRæ—FV×2‚—Ğ ¢2ÆWB5E$D„Ô$²&WF–â6öÆR÷væW'6†—öb6÷'F–ærÂv&÷VæF–ærÂÖ&²&÷VæG2À¢2æBW"Ö6ö×WF—F÷"W&f÷&Öæ6Rf&–æ6Rà¢6Æ7VÆF÷"Ò†æF–66Æ7VÆF÷"€¢öÆÆÖ÷W&ÃÖöÆÆÖ÷W&ÂÀ¢vööEöFc×vööEöFbÀ¢&W7VÇG5öFcÔæöæRÀ¢¢Ö&µ÷&W7VÇG2Ò6Æ7VÆF÷"æ6Æ7VÆFR€¢6ö×WF—F÷'3Ö6ö×WF—F÷%÷&V6÷&G2À¢vööC×vööBÀ¢WfVçEö6öFSÖWfVçEö6öFRÀ¢F÷W&æÖVçE÷&W7VÇG3×F÷W&æÖVçE÷&W7VÇG2÷"·ÒÀ¢ÖçVÅö÷fW'&–FW3×6VÆV7FVE÷fÇVW2À¢ ¢&WGW&âÖ&µ÷&W7VÇG5÷FõöF–7G2€¢Ö&µ÷&W7VÇG2À¢6ö×WF—F÷%÷&V6÷&G3Ö6ö×WF—F÷%÷&V6÷&G2À¢vööC×vööBÀ¢WfVçEö6öFSÖWfVçEö6öFRÀ¢&W7VÇG5öFc×&W7VÇG5öFbÀ¢öÆÆÖ÷W&ÃÖöÆÆÖ÷W&ÂÀ¢&VF–7F–öç5ö'•öæÖS×&VF–7F–öç5ö'•öæÖRÀ¢6VÆV7FVEö'•öæÖS×6VÆV7FVEö'•öæÖRÀ¢  ¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒĞ¢2W'6—7FVæ6R&÷VæF'¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒĞ  ¦FVb7&VFU÷&W7VÇE÷7F÷&R‚’Óâ&W7VÇE7F÷&S ¢""$7&VFR5E$D„Ô$²w2W'6—7FVçB&W7VÇB7F÷&RF‡&÷Vv‚F†RFFW"â"" ¢&WGW&â&W7VÇE7F÷&R‚  ¦FVb&V6÷&E÷&÷VæE÷&W7VÇG2€¢&÷VæEöö&¦V7C¢F–7E·7G"Âç•ÒÀ¢vööE÷6VÆV7F–öã¢F–7E·7G"Âç•ÒÀ¢7F÷&S¢&W7VÇE7F÷&RÀ¢’Óâ–çC ¢""%w&—FR6ö×ÆWFVBF÷W&æÖVçB&÷VæBFòF†R5E$D„Ô$²&W7VÇB7F÷&Râ"" ¢7GVÅ÷&W7VÇG2Ò&÷VæEöö&¦V7BævWB‚&7GVÅ÷&W7VÇG2"’÷"&÷VæEöö&¦V7BævWB‚'&W7VÇG2"’÷"·Ğ¢–bæ÷B7GVÅ÷&W7VÇG3 ¢&WGW&â  ¢&÷VæEöæÖRÒ&÷VæEöö&¦V7BævWB‚'&÷VæEöæÖR"Â""¢WfVçEö6öFRÒ7G"‡vööE÷6VÆV7F–öâævWB‚&WfVçB"Â%4""’’ç7G&—‚’çWW"‚¢7V6–W2Ò7G"‡vööE÷6VÆV7F–öâævWB‚'7V6–W2"Â%Væ¶æ÷vâ"’¢F–ÖWFW%öÖÒÒfÆöB‡vööE÷6VÆV7F–öâævWB‚'6—¦UöÖÒ"Â3’¢VÆ—G’Ò–çB‡vööE÷6VÆV7F–öâævWB‚'VÆ—G’"ÂR’¢†VEö–BÒ&÷VæEöæÖRç&WÆ6R‚""Â"Ò"’ç&WÆ6R‚"ò"Â"Ò"’–b&÷VæEöæÖRVÇ6R"  ¢–ç6W'FVBÒ ¢f÷"6ö×WF—F÷%öæÖRÂF–ÖU÷6V6öæG2–â7GVÅ÷&W7VÇG2æ—FV×2‚“ ¢–bF–ÖU÷6V6öæG2—2æöæS ¢6öçF–çVP¢G'“ ¢–b7F÷&Rç&V6÷&E÷&W7VÇB€¢6ö×WF—F÷%öæÖS×7G"†6ö×WF—F÷%öæÖR’À¢WfVçEö6öFSÖWfVçEö6öFRÀ¢F–ÖU÷6V6öæG3ÖfÆöB‡F–ÖU÷6V6öæG2’À¢7V6–W3×7V6–W2À¢F–ÖWFW%öÖÓÖF–ÖWFW%öÖÒÀ¢VÆ—G“×VÆ—G’À¢†VEö–CÖ†VEö–BÀ¢“ ¢–ç6W'FVB³Ò¢W†6WBW†6WF–öâ2W†3 ¢öÆörçv&æ–ær‚$6÷VÆBæ÷BW'6—7B&W7VÇBf÷"W3¢W2"Â6ö×WF—F÷%öæÖRÂW†2 ¢&WGW&â–ç6W'FV@  ¦FVbÖ–w&FUöW†6VÅ÷Fõ÷7F÷&R‡&W7VÇG5öFc¢BäFFg&ÖRÂ7F÷&S¢&W7VÇE7F÷&R’Óâ–çC ¢""$–FV×÷FVçFÇ’–×÷'BF†RW†6VÂ†—7F÷'’–çFò5E$D„Ô$²w2&W7VÇB7F÷&Râ"" ¢–b&W7VÇG5öFb—2æöæR÷"&W7VÇG5öFbæV×G“ ¢&WGW&â ¢&WGW&â7F÷&Ræ–×÷'Eög&öÕöFFg&ÖR‡&W7VÇG5öFbÂ6¶—öGWÆ–6FW3ÕG'VR  ¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒĞ¢26–×VÆF–öâæBf—&æW726ö×F–&–Æ—G’f6FW0¢2ÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒÒĞ  ¦FVbvWEö6ö×WF—F÷%÷f&–æ6U÷6V6öæG2†6ö×¢F–7E·7G"Âç•Ò’ÓâfÆöC ¢""$—6öÆFRF†R–ææVB5E$D„Ô$²&—fFRf&–æ6R†VÇW"–âöæR&÷VæF'’â"" ¢&WGW&âfÆöB…÷6Õ÷f&–æ6RåövWEö6ö×WF—F÷%÷f&–æ6U÷6V6öæG2†6ö×’  ¦FVb'VåöÖöçFUö6&Æõ÷6–×VÆF–öåöVæv–æR€¢6ö×WF—F÷'5÷v—F…öÖ&·3¢Æ—7E´F–7E·7G"Âç•ÕÒÀ¢¢¦·v&w2À¢’ÓâF–7E·7G"Âç•Ó ¢&WGW&â÷6Õ÷f&–æ6Rç'VåöÖöçFUö6&Æõ÷6–×VÆF–öâ€¢6ö×WF—F÷'5÷v—F…öÖ&·2À¢¢¦·v&w2À¢  ¦FVbvWEö•ö76W76ÖVçEöVæv–æR†æÇ—6—3¢F–7E·7G"Âç•Ò’Óâ7G# ¢&WGW&â÷6Õö76W75ö†æF–62†æÇ—6—2  ¦FVbvWEö6†×–öç6†—öæÇ—6—5öVæv–æR€¢æÇ—6—3¢F–7E·7G"Âç•ÒÀ¢&VF–7F–öç3¢Æ—7E´F–7EÒÀ¢’Óâ7G# ¢&WGW&â÷6Õö6†×–öç6†—öæÇ—6—2†æÇ—6—2Â&VF–7F–öç2  ¦FVb6–×VÆFUöæEö76W75öVæv–æR€¢6ö×WF—F÷'5÷v—F…öÖ&·3¢Æ—7E´F–7E·7G"Âç•ÕÒÀ¢¢À¢çVÕ÷6–×VÆF–öç3¢÷F–öæÅ¶–çEÒÒæöæRÀ¢6†÷s¢&ööÂÒG'VRÀ¢“ ¢&WGW&â÷6Õ÷6–×VÆFUöæEö76W72€¢6ö×WF—F÷'5÷v—F…öÖ&·2À¢çVÕ÷6–×VÆF–öç3ÖçVÕ÷6–×VÆF–öç2À¢6†÷s×6†÷rÀ¢