"""
Formula candidate grouping.

Группировка математических фрагментов в логические формулы.

Основной принцип:

    formula_candidate
        ↓
    anchor formula
        ↓
    formula_fragment*

При этом сохраняется fallback-режим
геометрической группировки для фрагментов,
у которых нет явного anchor.
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


# ============================================================================
# CANDIDATE TYPE
# ============================================================================


def is_formula_anchor(
    candidate: Dict[str, Any],
) -> bool:
    """
    Определяет, является ли candidate основным
    кандидатом математической формулы.

    Особенно важен detection_reason:

        formula_number_context

    Это означает, что классификатор обнаружил
    связь изображения с номером формулы.
    """

    role = candidate.get("role")

    reason = candidate.get(
        "detection_reason"
    )

    return (
        role == "formula_candidate"
        or reason == "formula_number_context"
    )


def is_formula_fragment(
    candidate: Dict[str, Any],
) -> bool:
    """
    Малый математический фрагмент.
    """

    return (
        candidate.get("role")
        == "formula_fragment"
    )


# ============================================================================
# GEOMETRY
# ============================================================================


def can_join_formula_group(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:

    bbox_a = a.get("bbox")
    bbox_b = b.get("bbox")

    if not bbox_a or not bbox_b:
        return False

    ay = bbox_center(
        bbox_a
    )[1]

    by = bbox_center(
        bbox_b
    )[1]

    if (
        abs(ay - by)
        > FORMULA_GROUP_CENTER_Y_TOLERANCE
    ):
        return False

    if (
        vertical_gap(
            bbox_a,
            bbox_b,
        )
        > FORMULA_GROUP_MAX_Y_GAP
    ):
        return False

    if (
        horizontal_gap(
            bbox_a,
            bbox_b,
        )
        > FORMULA_GROUP_MAX_X_GAP
    ):
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

    if (
        ratio
        > FORMULA_GROUP_HEIGHT_RATIO
    ):
        return False

    return True


# ============================================================================
# GROUPING
# ============================================================================


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

    groups: List[
        List[Dict[str, Any]]
    ] = []

    # ------------------------------------------------------------------------
    # 1. Сначала создаём группы вокруг anchor-кандидатов.
    # ------------------------------------------------------------------------

    anchors = [
        candidate
        for candidate in ordered
        if is_formula_anchor(candidate)
    ]

    anchor_groups: List[
        List[Dict[str, Any]]
    ] = []

    used_ids = set()

    for anchor in anchors:

        group = [anchor]

        used_ids.add(
            id(anchor)
        )

        # --------------------------------------------------------------
        # Ищем фрагменты рядом с anchor.
        # --------------------------------------------------------------

        for candidate in ordered:

            if candidate is anchor:
                continue

            if id(candidate) in used_ids:
                continue

            if not is_formula_fragment(
                candidate
            ):
                continue

            if not can_join_formula_group(
                anchor,
                candidate,
            ):
                continue

            group.append(
                candidate
            )

            used_ids.add(
                id(candidate)
            )

        anchor_groups.append(
            group
        )

    groups.extend(
        anchor_groups
    )

    # ------------------------------------------------------------------------
    # 2. Остаточные fragments.
    #
    # Они не относятся к явному anchor.
    # Для них сохраняем старый геометрический алгоритм.
    # ------------------------------------------------------------------------

    remaining = [
        candidate
        for candidate in ordered
        if id(candidate)
        not in used_ids
    ]

    for candidate in remaining:

        best_group = None
        best_distance = None

        for group in groups:

            # ----------------------------------------------------------
            # Если группа содержит anchor,
            # не разрешаем присоединять произвольный fragment,
            # который находится далеко от anchor.
            # ----------------------------------------------------------

            if not any(
                is_formula_anchor(member)
                for member in group
            ):
                reference = group[-1]

            else:
                reference = group[0]

            if not can_join_formula_group(
                reference,
                candidate,
            ):
                continue

            gap = horizontal_gap(
                reference["bbox"],
                candidate["bbox"],
            )

            if (
                best_distance is None
                or gap < best_distance
            ):
                best_group = group
                best_distance = gap

        if best_group is not None:
            best_group.append(
                candidate
            )
        else:
            groups.append(
                [candidate]
            )

    # ------------------------------------------------------------------------
    # 3. Формируем результат.
    # ------------------------------------------------------------------------

    result = []

    for group_id, members in enumerate(
        groups
    ):

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

                "members": len(
                    members
                ),

                "composite":
                    len(members) > 1,

                "parser_indices": [
                    item["parser_index"]
                    for item in members
                ],

                "source_indices": [
                    item["source_index"]
                    for item in members
                    if item.get(
                        "source_index"
                    )
                    is not None
                ],

                "xrefs": [
                    item["xref"]
                    for item in members
                    if item.get(
                        "xref"
                    )
                    is not None
                ],

                "bbox": bbox_union(
                    bboxes
                ),

                "formula_ids": [
                    item["formula_id"]
                    for item in members
                ],

                "confidence": round(
                    min(
                        item.get(
                            "confidence",
                            0.0,
                        )
                        for item in members
                    ),
                    3,
                ),
            }
        )

    return result
