"""
VKS Expert AI — formula ↔ number linking.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import (
    FORMULA_NUMBER_MAX_X_DISTANCE,
    FORMULA_NUMBER_MIN_LINK_SCORE,
    FORMULA_NUMBER_Y_TOLERANCE,
)

from .geometry import (
    bbox_center,
    safe_float,
)


def score_formula_number_link(
    formula: Dict[str, Any],
    number: Dict[str, Any],
) -> float:

    formula_bbox = formula.get("bbox")

    if not formula_bbox:
        return 0.0

    number_bbox = (
        number.get("number_estimated_bbox")
        or number.get("number_container_bbox")
    )

    if not number_bbox:
        return 0.0

    fx0, fy0, fx1, fy1 = map(
        safe_float,
        formula_bbox[:4],
    )

    nx0, ny0, nx1, ny1 = map(
        safe_float,
        number_bbox[:4],
    )

    fcx, fcy = bbox_center(formula_bbox)

    ncx, ncy = bbox_center(number_bbox)

    score = 0.0

    dy = abs(fcy - ncy)

    if dy <= 8:
        score += 60

    elif dy <= 18:
        score += 45

    elif dy <= 30:
        score += 30

    elif dy <= FORMULA_NUMBER_Y_TOLERANCE:
        score += 10

    else:
        return 0.0

    if nx0 >= fx1:

        gap = nx0 - fx1

        if gap <= 20:
            score += 45

        elif gap <= 60:
            score += 35

        elif gap <= 120:
            score += 25

        elif gap <= FORMULA_NUMBER_MAX_X_DISTANCE:
            score += 15

        else:
            return 0.0

    elif nx1 >= fx1:

        score += 20

    elif nx0 >= fx0:

        score += 10

    else:

        return 0.0

    if dy <= 10:
        score += 20

    if nx0 > 450:
        score += 20

    elif nx0 > 350:
        score += 10

    number_confidence = float(
        number.get(
            "confidence",
            0,
        )
    )

    score += number_confidence * 0.15

    return score


def link_formula_numbers(
    groups: List[Dict[str, Any]],
    numbers: List[Dict[str, Any]],
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:

    formula_records = []

    relations = []

    used_numbers = set()

    for group in groups:

        best_number = None
        best_score = 0.0

        for number_index, number in enumerate(numbers):

            if number_index in used_numbers:
                continue

            score = score_formula_number_link(
                group,
                number,
            )

            if score > best_score:

                best_score = score

                best_number = (
                    number_index,
                    number,
                )

        number_value = None
        number_parser_index = None
        number_source_index = None
        number_bbox = None
        number_estimated_bbox = None
        number_xref = None

        if (
            best_number is not None
            and best_score >= FORMULA_NUMBER_MIN_LINK_SCORE
        ):

            number_index, number = best_number

            used_numbers.add(number_index)

            number_value = number["number"]

            number_parser_index = (
                number["number_parser_index"]
            )

            number_source_index = (
                number["number_source_index"]
            )

            number_bbox = (
                number["number_container_bbox"]
            )

            number_estimated_bbox = (
                number["number_estimated_bbox"]
            )

            number_xref = number["number_xref"]

            relations.append(
                {
                    "group_id": group["group_id"],
                    "number": number_value,
                    "number_parser_index": number_parser_index,
                    "number_source_index": number_source_index,
                    "number_xref": number_xref,
                    "score": round(best_score, 3),
                }
            )

        formula_records.append(
            {
                "group_id": group["group_id"],

                "formula_ids": group["formula_ids"],

                "parser_indices": group["parser_indices"],

                "source_indices": group["source_indices"],

                "xrefs": group["xrefs"],

                "bbox": group["bbox"],

                "members": group["members"],

                "composite": group["composite"],

                "confidence": group["confidence"],

                "number": number_value,

                "number_parser_index": number_parser_index,

                "number_source_index": number_source_index,

                "number_xref": number_xref,

                "number_bbox": number_bbox,

                "number_estimated_bbox": number_estimated_bbox,

                "link_score": round(best_score, 3),
            }
        )

    return (
        formula_records,
        relations,
    )
