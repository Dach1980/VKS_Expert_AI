"""
VKS Expert AI — formula grouping.

ВАЖНО:
Этот модуль пока содержит baseline-алгоритм v0.6.
В следующем экспериментальном этапе именно этот алгоритм
будет переработан.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .config import (
    FORMULA_GROUP_CENTER_Y_TOLERANCE,
    FORMULA_GROUP_HEIGHT_RATIO,
    FORMULA_GROUP_MAX_X_GAP,
    FORMULA_GROUP_MAX_Y_GAP,
)

from .geometry import (
    bbox_center,
    bbox_height,
    bbox_union,
    horizontal_gap,
    vertical_gap,
)


def can_join_formula_group(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:

    bbox_a = a.get("bbox")
    bbox_b = b.get("bbox")

    if not bbox_a or not bbox_b:
        return False

    ay = bbox_center(bbox_a)[1]
    by = bbox_center(bbox_b)[1]

    if abs(ay - by) > FORMULA_GROUP_CENTER_Y_TOLERANCE:
        return False

    vgap = vertical_gap(
        bbox_a,
        bbox_b,
    )

    if vgap > FORMULA_GROUP_MAX_Y_GAP:
        return False

    hgap = horizontal_gap(
        bbox_a,
        bbox_b,
    )

    if hgap > FORMULA_GROUP_MAX_X_GAP:
        return False

    ha = max(
        bbox_height(bbox_a),
        1.0,
    )

    hb = max(
        bbox_height(bbox_b),
        1.0,
    )

    ratio = max(
        ha / hb,
        hb / ha,
    )

    if ratio > FORMULA_GROUP_HEIGHT_RATIO:
        return False

    return True


def build_formula_groups(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    if not candidates:
        return []

    ordered = sorted(
        candidates,
        key=lambda item: (
            item["bbox"][1],
            item["bbox"][0],
        ),
    )

    groups: List[List[Dict[str, Any]]] = []

    for candidate in ordered:

        best_group = None
        best_distance = None

        for group in groups:

            last = group[-1]

            if not can_join_formula_group(
                last,
                candidate,
            ):
                continue

            gap = horizontal_gap(
                last["bbox"],
                candidate["bbox"],
            )

            if (
                best_distance is None
                or gap < best_distance
            ):

                best_group = group
                best_distance = gap

        if best_group is not None:

            best_group.append(candidate)

        else:

            groups.append([candidate])

    result = []

    for group_id, members in enumerate(groups):

        members = sorted(
            members,
            key=lambda item: (
                item["bbox"][0],
                item["bbox"][1],
            ),
        )

        bboxes = [
            item["bbox"]
            for item in members
            if item.get("bbox")
        ]

        result.append(
            {
                "group_id": group_id,

                "members": len(members),

                "composite": len(members) > 1,

                "parser_indices": [
                    item["parser_index"]
                    for item in members
                ],

                "source_indices": [
                    item["source_index"]
                    for item in members
                    if item.get("source_index") is not None
                ],

                "xrefs": [
                    item["xref"]
                    for item in members
                    if item.get("xref") is not None
                ],

                "bbox": bbox_union(bboxes),

                "formula_ids": [
                    item["formula_id"]
                    for item in members
                ],

                "confidence": round(
                    min(
                        item.get("confidence", 0.0)
                        for item in members
                    ),
                    3,
                ),
            }
        )

    return result
