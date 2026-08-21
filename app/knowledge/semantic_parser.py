#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
======================================================================
VKS Expert AI — Semantic PDF Parser v0.5.1
======================================================================

Назначение:
    Построение семантического слоя PDF-документа поверх elements.json.

Основные задачи:
    1. Нормализация элементов страниц.
    2. Стабильная идентификация элементов через element_index.
    3. Поиск кандидатов математических формул.
    4. Группировка составных формул.
    5. Поиск номеров формул вида (1), (2), ...
    6. Связывание формулы с её номером.
    7. Формирование semantic.json.
    8. Подробный debug выбранной страницы.

Главное исправление v0.5.1:
    В v0.5 часть элементов имела element_index=None.
    Это приводило к тому, что все None попадали в один ключ
    group_by_element[None] и последняя группа затирала предыдущие.

    v0.5.1 гарантирует:
        element_index = позиция элемента внутри страницы

    Xref сохраняется отдельно:
        xref = PDF object reference

======================================================================
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# CONFIG
# =====================================================================

VERSION = "0.5.1"

DEFAULT_SOURCE = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\parsed"
    r"\SP_30.13330.2020.elements.json"
)

DEFAULT_OUTPUT = (
    r"D:\Projects\VKS_Expert_AI"
    r"\knowledge\parsed"
    r"\SP_30.13330.2020.semantic.json"
)

# Страница для детального debug.
DEBUG_PAGE = 12

# Минимальные размеры изображения-кандидата.
MIN_FORMULA_IMAGE_AREA = 180.0
MEDIUM_FORMULA_IMAGE_AREA = 400.0
LARGE_FORMULA_IMAGE_AREA = 700.0

# Максимальный размер элемента, который ещё может быть математическим
# символом/фрагментом формулы.
SMALL_MATH_MAX_WIDTH = 120.0
SMALL_MATH_MAX_HEIGHT = 80.0

# Максимальный вертикальный разрыв между элементами одной формулы.
FORMULA_GROUP_MAX_Y_GAP = 14.0

# Максимальный горизонтальный разрыв между соседними математическими
# изображениями в одной строке.
FORMULA_GROUP_MAX_X_GAP = 45.0

# Максимальное отношение высот элементов внутри одной группы.
FORMULA_GROUP_HEIGHT_RATIO = 3.5

# Максимальная вертикальная разница центров элементов группы.
FORMULA_GROUP_CENTER_Y_TOLERANCE = 28.0

# Номер формулы обычно находится ближе к правому краю страницы.
FORMULA_NUMBER_RIGHT_MARGIN_RATIO = 0.35

# Допустимый вертикальный диапазон номера относительно формулы.
FORMULA_NUMBER_Y_TOLERANCE = 45.0

# Допустимый горизонтальный диапазон номера.
FORMULA_NUMBER_MAX_X_DISTANCE = 180.0

# Минимальный score для автоматической связи.
FORMULA_NUMBER_MIN_LINK_SCORE = 45.0


# =====================================================================
# REGEX
# =====================================================================

FORMULA_NUMBER_RE = re.compile(
    r"(?<!\d)\(\s*(\d{1,4})\s*\)(?!\d)"
)

SECTION_NUMBER_RE = re.compile(
    r"^\s*\d+(?:\.\d+)*\s+"
)

BULLET_RE = re.compile(
    r"^\s*(?:[-–—•·]|\d+\))\s+"
)


# =====================================================================
# BASIC HELPERS
# =====================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bbox_area(bbox: Optional[List[float]]) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    x0, y0, x1, y1 = map(safe_float, bbox[:4])

    width = max(0.0, x1 - x0)
    height = max(0.0, y1 - y0)

    return width * height


def bbox_width(bbox: Optional[List[float]]) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[2]) - safe_float(bbox[0])
    )


def bbox_height(bbox: Optional[List[float]]) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[3]) - safe_float(bbox[1])
    )


def bbox_center(
    bbox: Optional[List[float]],
) -> Tuple[float, float]:

    if not bbox or len(bbox) < 4:
        return 0.0, 0.0

    x0, y0, x1, y1 = map(
        safe_float,
        bbox[:4],
    )

    return (
        (x0 + x1) / 2.0,
        (y0 + y1) / 2.0,
    )


def bbox_union(
    bboxes: List[List[float]],
) -> Optional[List[float]]:

    valid = [
        b
        for b in bboxes
        if b and len(b) >= 4
    ]

    if not valid:
        return None

    x0 = min(safe_float(b[0]) for b in valid)
    y0 = min(safe_float(b[1]) for b in valid)
    x1 = max(safe_float(b[2]) for b in valid)
    y1 = max(safe_float(b[3]) for b in valid)

    return [
        round(x0, 3),
        round(y0, 3),
        round(x1, 3),
        round(y1, 3),
    ]


def horizontal_gap(
    bbox_a: List[float],
    bbox_b: List[float],
) -> float:

    ax0, _, ax1, _ = bbox_a
    bx0, _, bx1, _ = bbox_b

    if ax1 < bx0:
        return bx0 - ax1

    if bx1 < ax0:
        return ax0 - bx1

    return 0.0


def vertical_gap(
    bbox_a: List[float],
    bbox_b: List[float],
) -> float:

    _, ay0, _, ay1 = bbox_a
    _, by0, _, by1 = bbox_b

    if ay1 < by0:
        return by0 - ay1

    if by1 < ay0:
        return ay0 - by1

    return 0.0


# =====================================================================
# ELEMENT NORMALIZATION
# =====================================================================

def normalize_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Гарантирует наличие стабильного element_index.

    ВАЖНО:

    elements.json может не содержать index вообще.

    Поэтому Semantic Parser использует позицию элемента
    внутри массива страницы как внутренний идентификатор.

    Например:

        position 0 -> index 0
        position 1 -> index 1
        ...
        position 30 -> index 30

    Если исходный index существует и является int,
    он сохраняется.

    Но для надёжности мы также записываем:

        parser_index

    который всегда равен физической позиции элемента.
    """

    normalized = []

    for position, original in enumerate(elements):

        if not isinstance(original, dict):
            continue

        element = dict(original)

        original_index = element.get("index")

        if isinstance(original_index, int):
            element["index"] = original_index
        else:
            element["index"] = position

        # Независимый внутренний идентификатор parser.
        element["parser_index"] = position

        normalized.append(element)

    return normalized


# =====================================================================
# ELEMENT IDENTITY
# =====================================================================

def get_element_index(
    element: Optional[Dict[str, Any]],
) -> Optional[int]:

    if not isinstance(element, dict):
        return None

    value = element.get("index")

    if isinstance(value, int):
        return value

    value = element.get("parser_index")

    if isinstance(value, int):
        return value

    return None


def get_element_xref(
    element: Optional[Dict[str, Any]],
) -> Optional[int]:

    if not isinstance(element, dict):
        return None

    value = element.get("xref")

    if isinstance(value, int):
        return value

    try:
        if value is not None:
            return int(value)
    except (TypeError, ValueError):
        pass

    return None


def element_identity(
    element: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "element_index": get_element_index(element),
        "xref": get_element_xref(element),
    }


# =====================================================================
# ELEMENT TYPE
# =====================================================================

def is_text_element(
    element: Dict[str, Any],
) -> bool:

    return element.get("type") == "text"


def is_image_element(
    element: Dict[str, Any],
) -> bool:

    return element.get("type") == "image"


# =====================================================================
# TEXT
# =====================================================================

def get_text(
    element: Dict[str, Any],
) -> str:

    value = element.get("text")

    if value is None:
        value = element.get("content")

    if value is None:
        return ""

    return str(value)


def normalize_text(text: str) -> str:

    return re.sub(
        r"\s+",
        " ",
        text.replace("\n", " "),
    ).strip()


# =====================================================================
# FORMULA CANDIDATE DETECTION
# =====================================================================

def is_math_like_image(
    element: Dict[str, Any],
) -> bool:

    if not is_image_element(element):
        return False

    bbox = element.get("bbox")

    area = bbox_area(bbox)
    width = bbox_width(bbox)
    height = bbox_height(bbox)

    if area <= 0:
        return False

    # Большие изображения считаем сильными кандидатами.
    if area >= LARGE_FORMULA_IMAGE_AREA:
        return True

    # Средние математические изображения.
    if area >= MEDIUM_FORMULA_IMAGE_AREA:
        return True

    # Маленькие элементы могут быть отдельными математическими
    # символами. Здесь используем более строгий фильтр.
    if (
        area >= MIN_FORMULA_IMAGE_AREA
        and width <= SMALL_MATH_MAX_WIDTH
        and height <= SMALL_MATH_MAX_HEIGHT
    ):
        return True

    return False


def formula_detection_reason(
    element: Dict[str, Any],
) -> Optional[str]:

    if not is_image_element(element):
        return None

    bbox = element.get("bbox")

    area = bbox_area(bbox)
    width = bbox_width(bbox)
    height = bbox_height(bbox)

    if area >= LARGE_FORMULA_IMAGE_AREA:
        return "large_image"

    if area >= MEDIUM_FORMULA_IMAGE_AREA:
        return "medium_math_image"

    if (
        area >= MIN_FORMULA_IMAGE_AREA
        and width <= SMALL_MATH_MAX_WIDTH
        and height <= SMALL_MATH_MAX_HEIGHT
    ):
        return "small_math_image"

    return None


# =====================================================================
# FORMULA CANDIDATES
# =====================================================================

def detect_formula_candidates(
    elements: List[Dict[str, Any]],
    page_number: int,
) -> List[Dict[str, Any]]:

    candidates = []

    for element in elements:

        if not is_math_like_image(element):
            continue

        index = get_element_index(element)
        xref = get_element_xref(element)

        # Критическая защита:
        # formula без идентификатора элемента не создаём.
        if index is None:
            continue

        reason = formula_detection_reason(
            element
        )

        bbox = element.get("bbox")

        formula_id = (
            f"SP30.13330_p"
            f"{page_number}"
            f"_e{index}"
            f"_x{xref if xref is not None else 'none'}"
        )

        candidate = {
            "formula_id": formula_id,
            "element_index": index,
            "xref": xref,
            "bbox": bbox,
            "detection_reason": reason,
            "area": round(
                bbox_area(bbox),
                3,
            ),
            "width": round(
                bbox_width(bbox),
                3,
            ),
            "height": round(
                bbox_height(bbox),
                3,
            ),
        }

        candidates.append(candidate)

    return candidates


# =====================================================================
# FORMULA GROUPING
# =====================================================================

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

        placed = False

        for group in groups:

            # Проверяем кандидата с последним элементом группы.
            last = group[-1]

            if can_join_formula_group(
                last,
                candidate,
            ):
                group.append(candidate)
                placed = True
                break

        if not placed:
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

        element_indices = [
            item["element_index"]
            for item in members
            if item.get("element_index") is not None
        ]

        xrefs = [
            item["xref"]
            for item in members
            if item.get("xref") is not None
        ]

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
                "element_indices": element_indices,
                "xrefs": xrefs,
                "bbox": bbox_union(bboxes),
                "formula_ids": [
                    item["formula_id"]
                    for item in members
                ],
            }
        )

    return result


# =====================================================================
# FORMULA NUMBER DETECTION
# =====================================================================

def extract_formula_number(
    text: str,
) -> Optional[int]:

    if not text:
        return None

    match = FORMULA_NUMBER_RE.search(text)

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def estimate_number_bbox(
    text_bbox: List[float],
    text: str,
) -> Optional[List[float]]:
    """
    Поскольку PDF text element может занимать всю строку,
    пытаемся оценить bbox непосредственно для "(N)".

    В большинстве документов номер находится справа.
    """

    if not text_bbox:
        return None

    match = FORMULA_NUMBER_RE.search(text)

    if not match:
        return None

    x0, y0, x1, y1 = map(
        safe_float,
        text_bbox[:4],
    )

    full_text = text or ""

    start = match.start()
    end = match.end()

    text_length = max(
        len(full_text),
        1,
    )

    # Пропорциональная оценка горизонтальной позиции.
    start_ratio = start / text_length
    end_ratio = end / text_length

    estimated_x0 = x0 + (
        (x1 - x0) * start_ratio
    )

    estimated_x1 = x0 + (
        (x1 - x0) * end_ratio
    )

    # Иногда proportional estimation получается слишком широкой.
    # Номер обычно занимает небольшую область.
    estimated_width = estimated_x1 - estimated_x0

    if estimated_width <= 0:
        estimated_width = min(
            35.0,
            x1 - x0,
        )

        estimated_x1 = x1
        estimated_x0 = max(
            x0,
            x1 - estimated_width,
        )

    return [
        round(estimated_x0, 3),
        round(y0, 3),
        round(estimated_x1, 3),
        round(y1, 3),
    ]


def detect_formula_numbers(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    numbers = []

    for element in elements:

        if not is_text_element(element):
            continue

        text = get_text(element)

        number = extract_formula_number(
            text
        )

        if number is None:
            continue

        index = get_element_index(element)

        if index is None:
            continue

        bbox = element.get("bbox")

        estimated_bbox = estimate_number_bbox(
            bbox,
            text,
        )

        numbers.append(
            {
                "number": number,

                "number_element_index": index,

                "number_xref": get_element_xref(
                    element
                ),

                # Весь text element.
                "number_container_bbox": bbox,

                # Оценочный bbox именно "(N)".
                "number_estimated_bbox": estimated_bbox,

                "text": text,
            }
        )

    return numbers


# =====================================================================
# FORMULA NUMBER LINKING
# =====================================================================

def score_formula_number_link(
    formula: Dict[str, Any],
    number: Dict[str, Any],
) -> float:

    formula_bbox = formula.get("bbox")

    if not formula_bbox:
        return 0.0

    number_bbox = (
        number.get(
            "number_estimated_bbox"
        )
        or number.get(
            "number_container_bbox"
        )
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

    fcx, fcy = bbox_center(
        formula_bbox
    )

    ncx, ncy = bbox_center(
        number_bbox
    )

    score = 0.0

    # ---------------------------------------------------------------
    # 1. Вертикальное расположение
    # ---------------------------------------------------------------

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

    # ---------------------------------------------------------------
    # 2. Номер должен находиться справа от формулы
    # ---------------------------------------------------------------

    if nx0 >= fx1:
        gap = nx0 - fx1

        if gap <= 20:
            score += 45

        elif gap <= 60:
            score += 35

        elif gap <= 120:
            score += 20

        elif gap <= FORMULA_NUMBER_MAX_X_DISTANCE:
            score += 10

    elif nx1 >= fx0:
        # Частичное горизонтальное пересечение.
        score += 15

    # ---------------------------------------------------------------
    # 3. Чем ближе центры по вертикали, тем лучше
    # ---------------------------------------------------------------

    if dy <= 10:
        score += 20

    # ---------------------------------------------------------------
    # 4. Номер должен быть относительно правым
    # ---------------------------------------------------------------

    if nx0 > 450:
        score += 20

    elif nx0 > 350:
        score += 10

    return score


def link_formula_numbers(
    candidates: List[Dict[str, Any]],
    groups: List[Dict[str, Any]],
    numbers: List[Dict[str, Any]],
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:

    if not candidates:
        return [], []

    # ---------------------------------------------------------------
    # Индекс candidate по element_index.
    # ---------------------------------------------------------------

    formula_by_element: Dict[int, Dict[str, Any]] = {}

    for candidate in candidates:

        index = candidate.get(
            "element_index"
        )

        if not isinstance(index, int):
            continue

        formula_by_element[index] = candidate

    # ---------------------------------------------------------------
    # Индекс групп по element_index.
    #
    # КРИТИЧЕСКАЯ ЗАЩИТА:
    # None сюда НИКОГДА не добавляем.
    # ---------------------------------------------------------------

    group_by_element: Dict[int, Dict[str, Any]] = {}

    for group in groups:

        for element_index in group.get(
            "element_indices",
            [],
        ):

            if not isinstance(
                element_index,
                int,
            ):
                continue

            group_by_element[
                element_index
            ] = group

    formula_records = []

    relations = []

    used_numbers = set()

    # ---------------------------------------------------------------
    # Обрабатываем каждую формулу.
    # ---------------------------------------------------------------

    for candidate in candidates:

        element_index = candidate.get(
            "element_index"
        )

        if not isinstance(
            element_index,
            int,
        ):
            continue

        group = group_by_element.get(
            element_index
        )

        best_number = None
        best_score = 0.0

        for number_index, number in enumerate(
            numbers
        ):

            if number_index in used_numbers:
                continue

            score = score_formula_number_link(
                candidate,
                number,
            )

            if score > best_score:
                best_score = score
                best_number = (
                    number_index,
                    number,
                )

        number_value = None
        number_element_index = None
        number_bbox = None
        number_estimated_bbox = None

        if (
            best_number is not None
            and best_score
            >= FORMULA_NUMBER_MIN_LINK_SCORE
        ):

            number_index, number = (
                best_number
            )

            used_numbers.add(
                number_index
            )

            number_value = number[
                "number"
            ]

            number_element_index = (
                number[
                    "number_element_index"
                ]
            )

            number_bbox = number[
                "number_container_bbox"
            ]

            number_estimated_bbox = (
                number[
                    "number_estimated_bbox"
                ]
            )

            relations.append(
                {
                    "formula_id": candidate[
                        "formula_id"
                    ],

                    "element_index": (
                        element_index
                    ),

                    "xref": candidate.get(
                        "xref"
                    ),

                    "group_id": (
                        group.get(
                            "group_id"
                        )
                        if group
                        else None
                    ),

                    "number": number_value,

                    "number_element_index": (
                        number_element_index
                    ),

                    "number_xref": number.get(
                        "number_xref"
                    ),

                    "score": round(
                        best_score,
                        3,
                    ),
                }
            )

        formula_records.append(
            {
                **candidate,

                "group_id": (
                    group.get(
                        "group_id"
                    )
                    if group
                    else None
                ),

                "group_members": (
                    group.get(
                        "members"
                    )
                    if group
                    else 1
                ),

                "composite": (
                    group.get(
                        "composite"
                    )
                    if group
                    else False
                ),

                "number": number_value,

                "number_element_index": (
                    number_element_index
                ),

                "number_bbox": number_bbox,

                "number_estimated_bbox": (
                    number_estimated_bbox
                ),

                "link_score": round(
                    best_score,
                    3,
                ),
            }
        )

    return (
        formula_records,
        relations,
    )


# =====================================================================
# CONTEXT
# =====================================================================

def find_previous_text_element(
    elements: List[Dict[str, Any]],
    element_index: int,
) -> Optional[Dict[str, Any]]:

    for position in range(
        len(elements) - 1,
        -1,
        -1,
    ):

        element = elements[position]

        index = get_element_index(
            element
        )

        if index is None:
            continue

        if index >= element_index:
            continue

        if is_text_element(element):

            text = normalize_text(
                get_text(element)
            )

            if text:
                return element

    return None


def find_next_text_element(
    elements: List[Dict[str, Any]],
    element_index: int,
) -> Optional[Dict[str, Any]]:

    for element in elements:

        index = get_element_index(
            element
        )

        if index is None:
            continue

        if index <= element_index:
            continue

        if is_text_element(element):

            text = normalize_text(
                get_text(element)
            )

            if text:
                return element

    return None


def enrich_formula_context(
    formula_records: List[Dict[str, Any]],
    elements: List[Dict[str, Any]],
) -> None:

    for formula in formula_records:

        index = formula.get(
            "element_index"
        )

        if not isinstance(index, int):
            continue

        previous = (
            find_previous_text_element(
                elements,
                index,
            )
        )

        following = (
            find_next_text_element(
                elements,
                index,
            )
        )

        if previous:

            formula[
                "previous_text"
            ] = normalize_text(
                get_text(previous)
            )

            formula[
                "previous_text_element_index"
            ] = get_element_index(
                previous
            )

        else:

            formula[
                "previous_text"
            ] = None

            formula[
                "previous_text_element_index"
            ] = None

        if following:

            formula[
                "next_text"
            ] = normalize_text(
                get_text(following)
            )

            formula[
                "next_text_element_index"
            ] = get_element_index(
                following
            )

        else:

            formula[
                "next_text"
            ] = None

            formula[
                "next_text_element_index"
            ] = None


# =====================================================================
# PAGE PROCESSING
# =====================================================================

def process_page(
    page: Dict[str, Any],
    page_number: int,
) -> Dict[str, Any]:

    raw_elements = page.get(
        "elements",
        [],
    )

    elements = normalize_page_elements(
        raw_elements
    )

    candidates = (
        detect_formula_candidates(
            elements,
            page_number,
        )
    )

    groups = build_formula_groups(
        candidates
    )

    numbers = detect_formula_numbers(
        elements
    )

    formula_records, relations = (
        link_formula_numbers(
            candidates,
            groups,
            numbers,
        )
    )

    enrich_formula_context(
        formula_records,
        elements,
    )

    return {
        "page_number": page_number,

        "elements_count": len(
            elements
        ),

        "formula_candidates": (
            candidates
        ),

        "formula_groups": groups,

        "formula_numbers": numbers,

        "formulas": formula_records,

        "formula_relations": relations,
    }


# =====================================================================
# DEBUG
# =====================================================================

def debug_page(
    page_number: int,
    page_result: Dict[str, Any],
    elements: List[Dict[str, Any]],
) -> None:

    print()
    print("=" * 70)
    print(
        f"ELEMENT DEBUG — PAGE {page_number}"
    )
    print("=" * 70)
    print()

    for position, element in enumerate(
        elements
    ):

        index = get_element_index(
            element
        )

        xref = get_element_xref(
            element
        )

        element_type = element.get(
            "type"
        )

        bbox = element.get(
            "bbox"
        )

        text = ""

        if element_type == "text":
            text = normalize_text(
                get_text(element)
            )

        if len(text) > 120:
            text = text[:120] + "..."

        print(
            f"#{position:<4}"
            f"{element_type:<8}"
            f"index={str(index):<4}"
            f"xref={str(xref):<4}"
            f"bbox={bbox} "
            f"{text!r}"
        )

    print()
    print("=" * 70)
    print(
        f"FORMULA DEBUG — PAGE {page_number}"
    )
    print("=" * 70)
    print()

    print("Formula candidates:")
    print("-" * 70)

    for formula in page_result[
        "formula_candidates"
    ]:

        print(
            f"formula_id="
            f"{formula['formula_id']}"
        )

        print(
            f"  element_index="
            f"{formula['element_index']}"
        )

        print(
            f"  xref="
            f"{formula['xref']}"
        )

        print(
            f"  bbox="
            f"{formula['bbox']}"
        )

        print(
            f"  detection_reason="
            f"{formula['detection_reason']}"
        )

        print(
            f"  area="
            f"{formula['area']}"
        )

        print()

    print("Formula groups:")
    print("-" * 70)

    for group in page_result[
        "formula_groups"
    ]:

        print(
            f"group="
            f"{group['group_id']} "
            f"members="
            f"{group['members']} "
            f"composite="
            f"{group['composite']}"
        )

        print(
            f"  indices="
            f"{group['element_indices']}"
        )

        print(
            f"  xrefs="
            f"{group['xrefs']}"
        )

        print(
            f"  bbox="
            f"{group['bbox']}"
        )

        print()

    print("Formula numbers:")
    print("-" * 70)

    for number in page_result[
        "formula_numbers"
    ]:

        print(
            f"number="
            f"{number['number']} "
            f"element_index="
            f"{number['number_element_index']}"
        )

        print(
            f"  container_bbox="
            f"{number['number_container_bbox']}"
        )

        print(
            f"  estimated_bbox="
            f"{number['number_estimated_bbox']}"
        )

        print(
            f"  text="
            f"{number['text']!r}"
        )

        print()

    print("Formula records:")
    print("-" * 70)

    for formula in page_result[
        "formulas"
    ]:

        print(
            f"formula_id="
            f"{formula['formula_id']}"
        )

        print(
            f"  element_index="
            f"{formula['element_index']}"
        )

        print(
            f"  xref="
            f"{formula['xref']}"
        )

        print(
            f"  group_id="
            f"{formula['group_id']}"
        )

        print(
            f"  group_members="
            f"{formula['group_members']}"
        )

        print(
            f"  composite="
            f"{formula['composite']}"
        )

        print(
            f"  number="
            f"{formula['number']}"
        )

        print(
            f"  number_element_index="
            f"{formula['number_element_index']}"
        )

        print(
            f"  link_score="
            f"{formula['link_score']}"
        )

        print(
            f"  number_bbox="
            f"{formula['number_bbox']}"
        )

        print(
            f"  estimated_number_bbox="
            f"{formula['number_estimated_bbox']}"
        )

        print()

    print("Formula relations:")
    print("-" * 70)

    for relation in page_result[
        "formula_relations"
    ]:

        print(
            f"formula="
            f"{relation['element_index']} "
            f"xref="
            f"{relation['xref']} "
            f"group="
            f"{relation['group_id']} "
            f"number="
            f"{relation['number']} "
            f"score="
            f"{relation['score']}"
        )

    print()


# =====================================================================
# VALIDATION
# =====================================================================

def validate_page_result(
    page_result: Dict[str, Any],
) -> List[str]:

    errors = []

    candidates = page_result[
        "formula_candidates"
    ]

    groups = page_result[
        "formula_groups"
    ]

    formulas = page_result[
        "formulas"
    ]

    relations = page_result[
        "formula_relations"
    ]

    # ---------------------------------------------------------------
    # 1. У кандидатов должен быть index.
    # ---------------------------------------------------------------

    for formula in candidates:

        if not isinstance(
            formula.get(
                "element_index"
            ),
            int,
        ):
            errors.append(
                "formula candidate "
                "without valid element_index"
            )

    # ---------------------------------------------------------------
    # 2. У групп не должно быть None.
    # ---------------------------------------------------------------

    for group in groups:

        for index in group.get(
            "element_indices",
            [],
        ):

            if not isinstance(
                index,
                int,
            ):
                errors.append(
                    "formula group contains "
                    "invalid element_index"
                )

    # ---------------------------------------------------------------
    # 3. Formula должна существовать в группе.
    # ---------------------------------------------------------------

    for formula in formulas:

        index = formula.get(
            "element_index"
        )

        group_id = formula.get(
            "group_id"
        )

        if index is None:
            errors.append(
                "formula has "
                "element_index=None"
            )

        if group_id is None:
            errors.append(
                f"formula {formula.get('formula_id')} "
                f"has no group"
            )

    # ---------------------------------------------------------------
    # 4. Relation должна указывать на реальную формулу.
    # ---------------------------------------------------------------

    formula_ids = {
        formula.get(
            "formula_id"
        )
        for formula in formulas
    }

    for relation in relations:

        if relation.get(
            "formula_id"
        ) not in formula_ids:

            errors.append(
                "relation points to "
                "unknown formula"
            )

    return errors


# =====================================================================
# STATISTICS
# =====================================================================

def build_statistics(
    pages: List[Dict[str, Any]],
    validation_errors: List[str],
) -> Dict[str, Any]:

    pages_count = len(
        pages
    )

    elements_count = sum(
        page.get(
            "elements_count",
            0,
        )
        for page in pages
    )

    images_count = 0

    formula_candidates_count = 0
    formula_groups_count = 0
    composite_groups_count = 0
    formula_numbers_count = 0
    relations_count = 0

    formulas_without_number = 0

    for page in pages:

        formula_candidates_count += len(
            page.get(
                "formula_candidates",
                [],
            )
        )

        formula_groups = page.get(
            "formula_groups",
            [],
        )

        formula_groups_count += len(
            formula_groups
        )

        composite_groups_count += sum(
            1
            for group in formula_groups
            if group.get(
                "composite"
            )
        )

        formula_numbers_count += len(
            page.get(
                "formula_numbers",
                [],
            )
        )

        relations_count += len(
            page.get(
                "formula_relations",
                [],
            )
        )

        formulas_without_number += sum(
            1
            for formula in page.get(
                "formulas",
                [],
            )
            if formula.get(
                "number"
            ) is None
        )

    return {
        "pages": pages_count,
        "elements": elements_count,
        "images": images_count,
        "formula_candidates": (
            formula_candidates_count
        ),
        "formula_groups": (
            formula_groups_count
        ),
        "composite_groups": (
            composite_groups_count
        ),
        "formula_numbers": (
            formula_numbers_count
        ),
        "formula_relations": (
            relations_count
        ),
        "formulas_without_number": (
            formulas_without_number
        ),
        "validation_errors": len(
            validation_errors
        ),
    }


# =====================================================================
# COUNT IMAGES
# =====================================================================

def count_images(
    source: Dict[str, Any],
) -> int:

    count = 0

    pages = source.get(
        "pages",
        [],
    )

    for page in pages:

        elements = page.get(
            "elements",
            [],
        )

        for element in elements:

            if element.get(
                "type"
            ) == "image":

                count += 1

    return count


# =====================================================================
# SOURCE STRUCTURE
# =====================================================================

def get_pages(
    source: Dict[str, Any],
) -> List[Dict[str, Any]]:

    pages = source.get(
        "pages"
    )

    if isinstance(
        pages,
        list,
    ):
        return pages

    # Иногда elements.json может содержать
    # pages внутри data.
    data = source.get(
        "data"
    )

    if isinstance(
        data,
        dict,
    ):

        pages = data.get(
            "pages"
        )

        if isinstance(
            pages,
            list,
        ):
            return pages

    return []


# =====================================================================
# MAIN PARSER
# =====================================================================

def parse_document(
    source_path: Path,
    output_path: Path,
) -> None:

    print("=" * 70)
    print(
        f"VKS Expert AI — "
        f"Semantic PDF Parser v{VERSION}"
    )
    print("=" * 70)
    print()

    print(
        f"Источник:\n"
        f"{source_path}"
    )
    print()

    print(
        "Загрузка elements.json..."
    )

    with source_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        source = json.load(
            file
        )

    pages = get_pages(
        source
    )

    print(
        f"Страниц: {len(pages)}"
    )
    print()

    print(
        "Семантический анализ..."
    )

    semantic_pages = []

    validation_errors = []

    debug_elements = None
    debug_result = None

    for page_position, page in enumerate(
        pages
    ):

        page_number = page.get(
            "page_number",
            page_position + 1,
        )

        print(
            f"Обработка страницы "
            f"{page_number}..."
        )

        page_result = process_page(
            page,
            page_number,
        )

        semantic_pages.append(
            page_result
        )

        page_errors = (
            validate_page_result(
                page_result
            )
        )

        for error in page_errors:

            validation_errors.append(
                f"page={page_number}: "
                f"{error}"
            )

        if page_number == DEBUG_PAGE:

            debug_elements = (
                normalize_page_elements(
                    page.get(
                        "elements",
                        [],
                    )
                )
            )

            debug_result = page_result

    # ---------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------

    statistics = build_statistics(
        semantic_pages,
        validation_errors,
    )

    statistics[
        "images"
    ] = count_images(
        source
    )

    # ---------------------------------------------------------------
    # Output document
    # ---------------------------------------------------------------

    result = {
        "parser": {
            "name": (
                "VKS Expert AI "
                "Semantic PDF Parser"
            ),
            "version": VERSION,
        },

        "source": str(
            source_path
        ),

        "statistics": statistics,

        "pages": semantic_pages,

        "validation": {
            "valid": (
                len(validation_errors)
                == 0
            ),

            "errors": (
                validation_errors
            ),
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # ---------------------------------------------------------------
    # DEBUG
    # ---------------------------------------------------------------

    if (
        debug_elements is not None
        and debug_result is not None
    ):

        debug_page(
            DEBUG_PAGE,
            debug_result,
            debug_elements,
        )

    # ---------------------------------------------------------------
    # Final output
    # ---------------------------------------------------------------

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)
    print()

    print(
        "Результат:"
    )

    print(
        output_path
    )

    print()
    print(
        "СТАТИСТИКА"
    )

    print("-" * 70)

    print(
        f"Страниц:"
        f"{statistics['pages']:>20}"
    )

    print(
        f"Элементов:"
        f"{statistics['elements']:>18}"
    )

    print(
        f"Изображений:"
        f"{statistics['images']:>16}"
    )

    print(
        f"Кандидатов формул:"
        f"{statistics['formula_candidates']:>10}"
    )

    print(
        f"Групп формул:"
        f"{statistics['formula_groups']:>15}"
    )

    print(
        f"Составных групп:"
        f"{statistics['composite_groups']:>12}"
    )

    print(
        f"Номеров формул:"
        f"{statistics['formula_numbers']:>13}"
    )

    print(
        f"Связанных формул:"
        f"{statistics['formula_relations']:>11}"
    )

    print(
        f"Формул без номера:"
        f"{statistics['formulas_without_number']:>10}"
    )

    print(
        f"Ошибок валидации:"
        f"{statistics['validation_errors']:>11}"
    )

    print()

    if validation_errors:

        print(
            "ПЕРВЫЕ ОШИБКИ ВАЛИДАЦИИ"
        )

        print("-" * 70)

        for error in validation_errors[
            :20
        ]:

            print(
                f"  {error}"
            )

        if len(
            validation_errors
        ) > 20:

            print(
                f"... и ещё "
                f"{len(validation_errors) - 20}"
            )

    else:

        print(
            "Валидация: OK"
        )


# =====================================================================
# CLI
# =====================================================================

def main() -> None:

    if len(sys.argv) >= 2:

        source_path = Path(
            sys.argv[1]
        )

    else:

        source_path = Path(
            DEFAULT_SOURCE
        )

    if len(sys.argv) >= 3:

        output_path = Path(
            sys.argv[2]
        )

    else:

        output_path = Path(
            DEFAULT_OUTPUT
        )

    if not source_path.exists():

        print(
            "ОШИБКА:"
        )

        print(
            f"Файл не найден:\n"
            f"{source_path}"
        )

        sys.exit(1)

    parse_document(
        source_path,
        output_path,
    )


if __name__ == "__main__":
    main()
    