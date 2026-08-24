
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
======================================================================
VKS Expert AI — Semantic PDF Parser v0.6
======================================================================

Назначение:
    Построение семантического слоя PDF-документа поверх elements.json.

v0.6:

    1. Нормализация элементов.
    2. Разделение:
           source_index
           parser_index
           xref
    3. Геометрический анализ изображений.
    4. Классификация изображений:
           symbol
           formula_fragment
           formula_candidate
           diagram_candidate
           unknown
    5. Группировка математических фрагментов.
    6. Поиск номеров формул.
    7. Связывание номера с группой формулы.
    8. Confidence score.
    9. Расширенная валидация.
   10. Подробный debug выбранной страницы.

ВАЖНЫЙ ПРИНЦИП:

    Этот parser НЕ распознаёт содержание изображения.

    Он определяет только структурную и геометрическую роль
    элемента.

    Распознавание самой математической формулы будет отдельным
    следующим этапом.
======================================================================
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# CONFIG
# =====================================================================

VERSION = "0.6"

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

DEBUG_PAGE = 12


# ---------------------------------------------------------------------
# Image classification
# ---------------------------------------------------------------------

SYMBOL_MAX_AREA = 1200.0

FORMULA_FRAGMENT_MIN_AREA = 180.0
FORMULA_FRAGMENT_MAX_AREA = 5000.0

FORMULA_CANDIDATE_MIN_AREA = 500.0

DIAGRAM_MIN_AREA = 5000.0

SMALL_MATH_MAX_WIDTH = 120.0
SMALL_MATH_MAX_HEIGHT = 80.0


# ---------------------------------------------------------------------
# Formula grouping
# ---------------------------------------------------------------------

FORMULA_GROUP_MAX_X_GAP = 45.0
FORMULA_GROUP_MAX_Y_GAP = 18.0
FORMULA_GROUP_CENTER_Y_TOLERANCE = 24.0

FORMULA_GROUP_HEIGHT_RATIO = 3.5


# ---------------------------------------------------------------------
# Formula number
# ---------------------------------------------------------------------

FORMULA_NUMBER_Y_TOLERANCE = 45.0
FORMULA_NUMBER_MAX_X_DISTANCE = 220.0

FORMULA_NUMBER_MIN_LINK_SCORE = 50.0


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

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def bbox_area(
    bbox: Optional[List[float]],
) -> float:

    if not bbox or len(bbox) < 4:
        return 0.0

    x0, y0, x1, y1 = map(
        safe_float,
        bbox[:4],
    )

    return max(
        0.0,
        x1 - x0,
    ) * max(
        0.0,
        y1 - y0,
    )


def bbox_width(
    bbox: Optional[List[float]],
) -> float:

    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[2])
        - safe_float(bbox[0]),
    )


def bbox_height(
    bbox: Optional[List[float]],
) -> float:

    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[3])
        - safe_float(bbox[1]),
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
        bbox
        for bbox in bboxes
        if bbox and len(bbox) >= 4
    ]

    if not valid:
        return None

    x0 = min(
        safe_float(b[0])
        for b in valid
    )

    y0 = min(
        safe_float(b[1])
        for b in valid
    )

    x1 = max(
        safe_float(b[2])
        for b in valid
    )

    y1 = max(
        safe_float(b[3])
        for b in valid
    )

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
# ELEMENT IDENTITY
# =====================================================================

def get_source_index(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get(
        "source_index"
    )

    if isinstance(value, int):
        return value

    return None


def get_parser_index(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get(
        "parser_index"
    )

    if isinstance(value, int):
        return value

    return None


def get_element_xref(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get(
        "xref"
    )

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
        "parser_index": get_parser_index(
            element
        ),

        "source_index": get_source_index(
            element
        ),

        "xref": get_element_xref(
            element
        ),
    }


# =====================================================================
# ELEMENT NORMALIZATION
# =====================================================================

def normalize_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    normalized = []

    for position, original in enumerate(
        elements
    ):

        if not isinstance(
            original,
            dict,
        ):
            continue

        element = dict(
            original
        )

        # -------------------------------------------------------------
        # Сохраняем исходный index.
        # -------------------------------------------------------------

        original_index = element.get(
            "index"
        )

        if isinstance(
            original_index,
            int,
        ):

            element[
                "source_index"
            ] = original_index

        else:

            element[
                "source_index"
            ] = None

        # -------------------------------------------------------------
        # Главный внутренний идентификатор.
        #
        # ВСЕГДА физическая позиция элемента.
        # -------------------------------------------------------------

        element[
            "parser_index"
        ] = position

        normalized.append(
            element
        )

    return normalized


# =====================================================================
# ELEMENT TYPE
# =====================================================================

def is_text_element(
    element: Dict[str, Any],
) -> bool:

    return element.get(
        "type"
    ) == "text"


def is_image_element(
    element: Dict[str, Any],
) -> bool:

    return element.get(
        "type"
    ) == "image"


# =====================================================================
# TEXT
# =====================================================================

def get_text(
    element: Dict[str, Any],
) -> str:

    value = element.get(
        "text"
    )

    if value is None:

        value = element.get(
            "content"
        )

    if value is None:
        return ""

    return str(
        value
    )


def normalize_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text.replace(
            "\n",
            " ",
        ),
    ).strip()


# =====================================================================
# PAGE GEOMETRY
# =====================================================================

def detect_page_geometry(
    page: Dict[str, Any],
    elements: List[Dict[str, Any]],
) -> Dict[str, float]:

    page_width = safe_float(
        page.get(
            "width"
        )
    )

    page_height = safe_float(
        page.get(
            "height"
        )
    )

    # Если размер страницы не указан,
    # вычисляем его по bbox элементов.

    if page_width <= 0:

        page_width = max(
            (
                safe_float(
                    element.get(
                        "bbox"
                    )[2]
                )
                for element in elements
                if element.get(
                    "bbox"
                )
                and len(
                    element.get(
                        "bbox"
                    )
                ) >= 4
            ),
            default=0.0,
        )

    if page_height <= 0:

        page_height = max(
            (
                safe_float(
                    element.get(
                        "bbox"
                    )[3]
                )
                for element in elements
                if element.get(
                    "bbox"
                )
                and len(
                    element.get(
                        "bbox"
                    )
                ) >= 4
            ),
            default=0.0,
        )

    return {
        "width": round(
            page_width,
            3,
        ),

        "height": round(
            page_height,
            3,
        ),
    }


def horizontal_region(
    bbox: List[float],
    page_width: float,
) -> str:

    if not bbox or page_width <= 0:
        return "unknown"

    center_x = bbox_center(
        bbox
    )[0]

    ratio = center_x / page_width

    if ratio < 0.33:
        return "left"

    if ratio < 0.67:
        return "center"

    return "right"


# =====================================================================
# IMAGE CLASSIFICATION
# =====================================================================

def classify_image(
    element: Dict[str, Any],
) -> Tuple[str, str, float]:

    bbox = element.get(
        "bbox"
    )

    area = bbox_area(
        bbox
    )

    width = bbox_width(
        bbox
    )

    height = bbox_height(
        bbox
    )

    if area <= 0:
        return (
            "unknown",
            "invalid_geometry",
            0.0,
        )

    # -------------------------------------------------------------
    # 1. Очень крупные изображения.
    #
    # Проверяем ПЕРВЫМИ, иначе они попадут в formula_candidate.
    # -------------------------------------------------------------

    if area >= DIAGRAM_MIN_AREA:

        if height > 0:

            aspect_ratio = (
                width / height
            )

            if aspect_ratio >= 8.0:

                return (
                    "diagram_candidate",
                    "large_extreme_aspect_ratio",
                    0.75,
                )

        return (
            "diagram_candidate",
            "large_image",
            0.70,
        )

    # -------------------------------------------------------------
    # 2. Очень маленькие изображения.
    #
    # По умолчанию считаем их символами.
    # -------------------------------------------------------------

    if area <= SYMBOL_MAX_AREA:

        # ---------------------------------------------------------
        # Маленький объект может быть математическим фрагментом,
        # если его геометрия похожа на математический символ.
        #
        # Пока не переводим все маленькие изображения
        # автоматически в formula_fragment.
        # ---------------------------------------------------------

        if (
            width <= SMALL_MATH_MAX_WIDTH
            and height <= SMALL_MATH_MAX_HEIGHT
            and area >= FORMULA_FRAGMENT_MIN_AREA
        ):

            return (
                "formula_fragment",
                "small_math_geometry",
                0.75,
            )

        return (
            "symbol",
            "small_image",
            0.80,
        )

    # -------------------------------------------------------------
    # 3. Средние изображения.
    # -------------------------------------------------------------

    if area >= FORMULA_CANDIDATE_MIN_AREA:

        if height > 0:

            aspect_ratio = (
                width / height
            )

            if aspect_ratio >= 8.0:

                return (
                    "diagram_candidate",
                    "medium_extreme_aspect_ratio",
                    0.55,
                )

        return (
            "formula_candidate",
            "medium_math_geometry",
            0.65,
        )

    # -------------------------------------------------------------
    # 4. Всё остальное.
    # -------------------------------------------------------------

    return (
        "unknown",
        "unclassified",
        0.20,
    )

# =====================================================================
# ELEMENT ENRICHMENT
# =====================================================================

def enrich_element(
    element: Dict[str, Any],
    page_geometry: Dict[str, float],
) -> Dict[str, Any]:

    result = dict(
        element
    )

    bbox = element.get(
        "bbox"
    )

    result[
        "identity"
    ] = element_identity(
        element
    )

    if is_image_element(
        element
    ):

        area = bbox_area(
            bbox
        )

        width = bbox_width(
            bbox
        )

        height = bbox_height(
            bbox
        )

        result[
            "geometry"
        ] = {
            "width": round(
                width,
                3,
            ),

            "height": round(
                height,
                3,
            ),

            "area": round(
                area,
                3,
            ),

            "center": [
                round(
                    bbox_center(
                        bbox
                    )[0],
                    3,
                ),

                round(
                    bbox_center(
                        bbox
                    )[1],
                    3,
                ),
            ],

            "horizontal_region":
                horizontal_region(
                    bbox,
                    page_geometry[
                        "width"
                    ],
                ),
        }

        (
            role,
            reason,
            confidence,
        ) = classify_image(
            element
        )

        result[
            "semantic_role"
        ] = role

        result[
            "classification_reason"
        ] = reason

        result[
            "classification_confidence"
        ] = confidence

    elif is_text_element(
        element
    ):

        text = normalize_text(
            get_text(
                element
            )
        )

        result[
            "text_normalized"
        ] = text

        number = extract_formula_number(
            text
        )

        if number is not None:

            result[
                "semantic_role"
            ] = "formula_number"

        else:

            result[
                "semantic_role"
            ] = "text"

    return result


# =====================================================================
# FORMULA CANDIDATES
# =====================================================================

def is_formula_candidate(
    element: Dict[str, Any],
) -> bool:

    return element.get(
        "semantic_role"
    ) in {
        "formula_fragment",
        "formula_candidate",
    }


def detect_formula_candidates(
    elements: List[Dict[str, Any]],
    page_number: int,
) -> List[Dict[str, Any]]:

    candidates = []

    for element in elements:

        if not is_formula_candidate(
            element
        ):
            continue

        parser_index = get_parser_index(
            element
        )

        if parser_index is None:
            continue

        xref = get_element_xref(
            element
        )

        bbox = element.get(
            "bbox"
        )

        geometry = element.get(
            "geometry",
            {},
        )

        role = element.get(
            "semantic_role"
        )

        confidence = safe_float(
            element.get(
                "classification_confidence"
            )
        )

        formula_id = (
            f"SP30.13330"
            f"_p{page_number}"
            f"_e{parser_index}"
            f"_x"
            f"{xref if xref is not None else 'none'}"
        )

        candidates.append(
            {
                "formula_id": formula_id,

                "parser_index":
                    parser_index,

                "source_index":
                    get_source_index(
                        element
                    ),

                "xref": xref,

                "bbox": bbox,

                "role": role,

                "detection_reason":
                    element.get(
                        "classification_reason"
                    ),

                "confidence":
                    round(
                        confidence,
                        3,
                    ),

                "area":
                    geometry.get(
                        "area",
                        0,
                    ),

                "width":
                    geometry.get(
                        "width",
                        0,
                    ),

                "height":
                    geometry.get(
                        "height",
                        0,
                    ),

                "horizontal_region":
                    geometry.get(
                        "horizontal_region"
                    ),
            }
        )

    return candidates


# =====================================================================
# FORMULA GROUPING
# =====================================================================

def can_join_formula_group(
    a: Dict[str, Any],
    b: Dict[str, Any],
) -> bool:

    bbox_a = a.get(
        "bbox"
    )

    bbox_b = b.get(
        "bbox"
    )

    if not bbox_a or not bbox_b:
        return False

    ay = bbox_center(
        bbox_a
    )[1]

    by = bbox_center(
        bbox_b
    )[1]

    if abs(
        ay - by
    ) > FORMULA_GROUP_CENTER_Y_TOLERANCE:

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
        bbox_height(
            bbox_a
        ),
        1.0,
    )

    hb = max(
        bbox_height(
            bbox_b
        ),
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

    groups: List[
        List[Dict[str, Any]]
    ] = []

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

            best_group.append(
                candidate
            )

        else:

            groups.append(
                [candidate]
            )

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
            if item.get(
                "bbox"
            )
        ]

        result.append(
            {
                "group_id":
                    group_id,

                "members":
                    len(members),

                "composite":
                    len(members) > 1,

                "parser_indices": [
                    item[
                        "parser_index"
                    ]
                    for item in members
                ],

                "source_indices": [
                    item[
                        "source_index"
                    ]
                    for item in members
                    if item.get(
                        "source_index"
                    ) is not None
                ],

                "xrefs": [
                    item["xref"]
                    for item in members
                    if item.get(
                        "xref"
                    ) is not None
                ],

                "bbox":
                    bbox_union(
                        bboxes
                    ),

                "formula_ids": [
                    item[
                        "formula_id"
                    ]
                    for item in members
                ],

                "confidence":
                    round(
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


# =====================================================================
# FORMULA NUMBERS
# =====================================================================

def extract_formula_number(
    text: str,
) -> Optional[int]:

    if not text:
        return None

    match = FORMULA_NUMBER_RE.search(
        text
    )

    if not match:
        return None

    try:

        return int(
            match.group(1)
        )

    except ValueError:

        return None

def estimate_number_bbox(
    text_bbox: List[float],
    text: str,
) -> Optional[List[float]]:
    """
    Оценивает bbox непосредственно номера формулы.

    Основной принцип:

    Если "(N)" находится в конце текстового элемента,
    считаем, что номер расположен у правого края
    текстового bbox.

    Например:

        text = ", (2)"

    и bbox:

        [70, 648, 560, 688]

    превращается примерно в:

        [525, 648, 560, 688]

    вместо пропорционального bbox всей строки.
    """

    if not text_bbox:
        return None

    match = FORMULA_NUMBER_RE.search(
        text
    )

    if not match:
        return None

    x0, y0, x1, y1 = map(
        safe_float,
        text_bbox[:4],
    )

    if x1 <= x0:
        return None

    # ---------------------------------------------------------------
    # Номер находится в конце строки.
    #
    # Это наиболее типичный случай для PDF:
    #
    #     ..., (1)
    #
    # ---------------------------------------------------------------

    suffix = text[
        match.end():
    ].strip()

    if not suffix:

        # Реальная ширина номера в PDF обычно находится
        # в диапазоне примерно 20–40 pt.
        #
        # Берём консервативную ширину.
        number_width = min(
            38.0,
            x1 - x0,
        )

        estimated_x1 = x1

        estimated_x0 = max(
            x0,
            x1 - number_width,
        )

        return [
            round(estimated_x0, 3),
            round(y0, 3),
            round(estimated_x1, 3),
            round(y1, 3),
        ]

    # ---------------------------------------------------------------
    # Если после "(N)" ещё есть текст,
    # используем пропорциональную оценку.
    # ---------------------------------------------------------------

    full_text = text or ""

    text_length = max(
        len(full_text),
        1,
    )

    start_ratio = (
        match.start()
        / text_length
    )

    end_ratio = (
        match.end()
        / text_length
    )

    estimated_x0 = (
        x0
        + (x1 - x0)
        * start_ratio
    )

    estimated_x1 = (
        x0
        + (x1 - x0)
        * end_ratio
    )

    # ---------------------------------------------------------------
    # Защита от слишком широкого bbox.
    # ---------------------------------------------------------------

    max_number_width = min(
        45.0,
        x1 - x0,
    )

    if (
        estimated_x1
        - estimated_x0
        > max_number_width
    ):

        estimated_x1 = min(
            x1,
            estimated_x0
            + max_number_width,
        )

    if estimated_x1 <= estimated_x0:

        estimated_x1 = x1

        estimated_x0 = max(
            x0,
            x1 - max_number_width,
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

        # -----------------------------------------------------------
        # Идентификаторы элемента
        # -----------------------------------------------------------

        parser_index = get_parser_index(
            element
        )

        if parser_index is None:
            continue

        source_index = get_source_index(
            element
        )

        xref = get_element_xref(
            element
        )

        # -----------------------------------------------------------
        # Геометрия
        # -----------------------------------------------------------

        bbox = element.get(
            "bbox"
        )

        estimated_bbox = (
            estimate_number_bbox(
                bbox,
                text,
            )
        )

        # -----------------------------------------------------------
        # Нормализованный текст
        # -----------------------------------------------------------

        normalized = normalize_text(
            text
        )

        # -----------------------------------------------------------
        # Позиция номера внутри текстового элемента
        # -----------------------------------------------------------

        match = FORMULA_NUMBER_RE.search(
            text
        )

        if match:

            prefix = normalize_text(
                text[:match.start()]
            )

            suffix = normalize_text(
                text[match.end():]
            )

        else:

            prefix = ""
            suffix = ""

        # -----------------------------------------------------------
        # Confidence кандидата
        # -----------------------------------------------------------

        confidence = 0.0

        # Номер находится в конце строки.
        if not suffix:
            confidence += 50.0

        # Перед номером обычно стоит запятая.
        if prefix.endswith(","):
            confidence += 20.0

        # Очень короткий контейнер — хороший кандидат.
        if len(normalized) <= 12:
            confidence += 20.0

        # Текст только из номера/запятой.
        if re.fullmatch(
            r"[,\s]*\(\s*\d{1,4}\s*\)",
            normalized,
        ):
            confidence += 30.0

        # -----------------------------------------------------------
        # Результат
        # -----------------------------------------------------------

        numbers.append(
            {
                "number": number,

                # ---------------------------------------------------
                # Идентификаторы исходного элемента
                # ---------------------------------------------------

                "number_parser_index":
                    parser_index,

                "number_source_index":
                    source_index,

                "number_xref":
                    xref,

                # ---------------------------------------------------
                # Геометрия
                # ---------------------------------------------------

                "number_container_bbox":
                    bbox,

                "number_estimated_bbox":
                    estimated_bbox,

                # ---------------------------------------------------
                # Текст
                # ---------------------------------------------------

                "text":
                    text,

                "prefix":
                    prefix,

                "suffix":
                    suffix,

                # ---------------------------------------------------
                # Confidence
                # ---------------------------------------------------

                "confidence":
                    round(
                        min(
                            confidence,
                            100.0,
                        ),
                        3,
                    ),
            }
        )

    return numbers

# =====================================================================
# NUMBER LINKING
# =====================================================================

def score_formula_number_link(
    formula: Dict[str, Any],
    number: Dict[str, Any],
) -> float:

    formula_bbox = formula.get(
        "bbox"
    )

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

    # ===============================================================
    # 1. Вертикальное совпадение
    # ===============================================================

    dy = abs(
        fcy - ncy
    )

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

    # ===============================================================
    # 2. Номер справа от формулы
    # ===============================================================

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
            # Слишком далеко.
            return 0.0

    elif nx1 >= fx1:

        # Небольшое горизонтальное пересечение.
        score += 20

    elif nx0 >= fx0:

        # Номер оказался внутри горизонтального диапазона
        # формулы. Такое возможно для нестандартной верстки.
        score += 10

    else:

        # Номер полностью левее формулы.
        return 0.0

    # ===============================================================
    # 3. Очень хорошее вертикальное выравнивание
    # ===============================================================

    if dy <= 10:
        score += 20

    # ===============================================================
    # 4. Номер должен находиться справа на странице
    # ===============================================================

    page_right = max(
        fx1,
        nx1,
    )

    # Сохраняем старое правило,
    # но не привязываемся жёстко к конкретному формату страницы.
    if nx0 > 450:
        score += 20

    elif nx0 > 350:
        score += 10

    # ===============================================================
    # 5. Confidence самого кандидата
    # ===============================================================

    number_confidence = safe_float(
        number.get(
            "confidence",
            0,
        )
    )

    score += (
        number_confidence
        * 0.15
    )

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

    # -------------------------------------------------------------
    # Работаем именно с группами.
    # -------------------------------------------------------------

    for group in groups:

        best_number = None
        best_score = 0.0

        for number_index, number in enumerate(
            numbers
        ):

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

            number_parser_index = (
                number[
                    "number_parser_index"
                ]
            )

            number_source_index = (
                number[
                    "number_source_index"
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

            number_xref = number[
                "number_xref"
            ]

            relations.append(
                {
                    "group_id":
                        group[
                            "group_id"
                        ],

                    "number":
                        number_value,

                    "number_parser_index":
                        number_parser_index,

                    "number_source_index":
                        number_source_index,

                    "number_xref":
                        number_xref,

                    "score":
                        round(
                            best_score,
                            3,
                        ),
                }
            )

        # ---------------------------------------------------------
        # Record для каждой группы.
        # ---------------------------------------------------------

        formula_records.append(
            {
                "group_id":
                    group[
                        "group_id"
                    ],

                "formula_ids":
                    group[
                        "formula_ids"
                    ],

                "parser_indices":
                    group[
                        "parser_indices"
                    ],

                "source_indices":
                    group[
                        "source_indices"
                    ],

                "xrefs":
                    group[
                        "xrefs"
                    ],

                "bbox":
                    group[
                        "bbox"
                    ],

                "members":
                    group[
                        "members"
                    ],

                "composite":
                    group[
                        "composite"
                    ],

                "confidence":
                    group[
                        "confidence"
                    ],

                "number":
                    number_value,

                "number_parser_index":
                    number_parser_index,

                "number_source_index":
                    number_source_index,

                "number_xref":
                    number_xref,

                "number_bbox":
                    number_bbox,

                "number_estimated_bbox":
                    number_estimated_bbox,

                "link_score":
                    round(
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
    parser_index: int,
) -> Optional[Dict[str, Any]]:

    for element in reversed(
        elements
    ):

        index = get_parser_index(
            element
        )

        if index is None:
            continue

        if index >= parser_index:
            continue

        if is_text_element(
            element
        ):

            text = normalize_text(
                get_text(
                    element
                )
            )

            if text:
                return element

    return None


def find_next_text_element(
    elements: List[Dict[str, Any]],
    parser_index: int,
) -> Optional[Dict[str, Any]]:

    for element in elements:

        index = get_parser_index(
            element
        )

        if index is None:
            continue

        if index <= parser_index:
            continue

        if is_text_element(
            element
        ):

            text = normalize_text(
                get_text(
                    element
                )
            )

            if text:
                return element

    return None


def enrich_formula_context(
    formula_records: List[Dict[str, Any]],
    elements: List[Dict[str, Any]],
) -> None:

    for formula in formula_records:

        indices = formula.get(
            "parser_indices",
            [],
        )

        if not indices:
            continue

        first_index = min(
            indices
        )

        last_index = max(
            indices
        )

        previous = (
            find_previous_text_element(
                elements,
                first_index,
            )
        )

        following = (
            find_next_text_element(
                elements,
                last_index,
            )
        )

        formula[
            "previous_text"
        ] = (
            normalize_text(
                get_text(
                    previous
                )
            )
            if previous
            else None
        )

        formula[
            "previous_text_parser_index"
        ] = (
            get_parser_index(
                previous
            )
            if previous
            else None
        )

        formula[
            "next_text"
        ] = (
            normalize_text(
                get_text(
                    following
                )
            )
            if following
            else None
        )

        formula[
            "next_text_parser_index"
        ] = (
            get_parser_index(
                following
            )
            if following
            else None
        )


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

    page_geometry = detect_page_geometry(
        page,
        elements,
    )

    enriched_elements = [
        enrich_element(
            element,
            page_geometry,
        )
        for element in elements
    ]

    candidates = detect_formula_candidates(
        enriched_elements,
        page_number,
    )

    groups = build_formula_groups(
        candidates
    )

    numbers = detect_formula_numbers(
        enriched_elements
    )

    formula_records, relations = (
        link_formula_numbers(
            groups,
            numbers,
        )
    )

    enrich_formula_context(
        formula_records,
        enriched_elements,
    )

    return {
        "page_number":
            page_number,

        "page_geometry":
            page_geometry,

        "elements_count":
            len(
                enriched_elements
            ),

        "elements":
            enriched_elements,

        "formula_candidates":
            candidates,

        "formula_groups":
            groups,

        "formula_numbers":
            numbers,

        "formulas":
            formula_records,

        "formula_relations":
            relations,
    }


# =====================================================================
# VALIDATION
# =====================================================================

def validate_page_result(
    page_result: Dict[str, Any],
) -> List[str]:

    errors = []

    elements = page_result.get(
        "elements",
        [],
    )

    candidates = page_result.get(
        "formula_candidates",
        [],
    )

    groups = page_result.get(
        "formula_groups",
        [],
    )

    formulas = page_result.get(
        "formulas",
        [],
    )

    relations = page_result.get(
        "formula_relations",
        [],
    )

    element_indices = {
        get_parser_index(
            element
        )
        for element in elements
    }

    # -------------------------------------------------------------
    # 1. У каждого элемента должен быть parser_index.
    # -------------------------------------------------------------

    for element in elements:

        index = get_parser_index(
            element
        )

        if not isinstance(
            index,
            int,
        ):

            errors.append(
                "element without valid "
                "parser_index"
            )

    # -------------------------------------------------------------
    # 2. Кандидаты должны ссылаться на реальные элементы.
    # -------------------------------------------------------------

    for candidate in candidates:

        index = candidate.get(
            "parser_index"
        )

        if index not in element_indices:

            errors.append(
                "formula candidate "
                "points to unknown "
                "parser_index"
            )

    # -------------------------------------------------------------
    # 3. Группы.
    # -------------------------------------------------------------

    group_ids = set()

    for group in groups:

        group_id = group.get(
            "group_id"
        )

        if group_id in group_ids:

            errors.append(
                f"duplicate group_id "
                f"{group_id}"
            )

        group_ids.add(
            group_id
        )

        for index in group.get(
            "parser_indices",
            [],
        ):

            if index not in element_indices:

                errors.append(
                    "formula group contains "
                    "unknown parser_index"
                )

    # -------------------------------------------------------------
    # 4. Формулы должны иметь группу.
    # -------------------------------------------------------------

    valid_group_ids = {
        group.get(
            "group_id"
        )
        for group in groups
    }

    for formula in formulas:

        group_id = formula.get(
            "group_id"
        )

        if group_id not in valid_group_ids:

            errors.append(
                "formula points to "
                "unknown group"
            )

    # -------------------------------------------------------------
    # 5. Relations.
    # -------------------------------------------------------------

    for relation in relations:

        group_id = relation.get(
            "group_id"
        )

        if group_id not in valid_group_ids:

            errors.append(
                "relation points to "
                "unknown group"
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

    images_count = sum(
        1
        for page in pages
        for element in page.get(
            "elements",
            [],
        )
        if is_image_element(
            element
        )
    )

    symbols_count = sum(
        1
        for page in pages
        for element in page.get(
            "elements",
            [],
        )
        if element.get(
            "semantic_role"
        ) == "symbol"
    )

    formula_fragments_count = sum(
        1
        for page in pages
        for element in page.get(
            "elements",
            [],
        )
        if element.get(
            "semantic_role"
        ) == "formula_fragment"
    )

    diagram_candidates_count = sum(
        1
        for page in pages
        for element in page.get(
            "elements",
            [],
        )
        if element.get(
            "semantic_role"
        ) == "diagram_candidate"
    )

    formula_candidates_count = sum(
        len(
            page.get(
                "formula_candidates",
                [],
            )
        )
        for page in pages
    )

    formula_groups_count = sum(
        len(
            page.get(
                "formula_groups",
                [],
            )
        )
        for page in pages
    )

    composite_groups_count = sum(
        sum(
            1
            for group in page.get(
                "formula_groups",
                []
            )
            if group.get(
                "composite"
            )
        )
        for page in pages
    )

    formula_numbers_count = sum(
        len(
            page.get(
                "formula_numbers",
                [],
            )
        )
        for page in pages
    )

    relations_count = sum(
        len(
            page.get(
                "formula_relations",
                [],
            )
        )
        for page in pages
    )

    formulas_without_number = sum(
        sum(
            1
            for formula in page.get(
                "formulas",
                []
            )
            if formula.get(
                "number"
            ) is None
        )
        for page in pages
    )

    return {
        "pages":
            pages_count,

        "elements":
            elements_count,

        "images":
            images_count,

        "symbols":
            symbols_count,

        "formula_fragments":
            formula_fragments_count,

        "diagram_candidates":
            diagram_candidates_count,

        "formula_candidates":
            formula_candidates_count,

        "formula_groups":
            formula_groups_count,

        "composite_groups":
            composite_groups_count,

        "formula_numbers":
            formula_numbers_count,

        "formula_relations":
            relations_count,

        "formulas_without_number":
            formulas_without_number,

        "validation_errors":
            len(
                validation_errors
            ),
    }


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
# DEBUG
# =====================================================================

def debug_page(
    page_number: int,
    page_result: Dict[str, Any],
) -> None:

    print()
    print("=" * 80)
    print(
        f"ELEMENT DEBUG — PAGE {page_number}"
    )
    print("=" * 80)
    print()

    print(
        "Page geometry:",
        page_result[
            "page_geometry"
        ],
    )

    print()

    for element in page_result[
        "elements"
    ]:

        parser_index = get_parser_index(
            element
        )

        source_index = get_source_index(
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

        role = element.get(
            "semantic_role",
            "",
        )

        text = ""

        if is_text_element(
            element
        ):

            text = normalize_text(
                get_text(
                    element
                )
            )

        if len(text) > 100:
            text = text[:100] + "..."

        print(
            f"#{parser_index:<4} "
            f"type={element_type:<7} "
            f"source={str(source_index):<4} "
            f"xref={str(xref):<4} "
            f"role={role:<20} "
            f"bbox={bbox} "
            f"{text!r}"
        )

    print()
    print("=" * 80)
    print(
        f"FORMULA GROUP DEBUG — PAGE {page_number}"
    )
    print("=" * 80)
    print()

    for group in page_result[
        "formula_groups"
    ]:

        print(
            f"group={group['group_id']} "
            f"members={group['members']} "
            f"composite={group['composite']} "
            f"confidence={group['confidence']}"
        )

        print(
            f"  parser_indices="
            f"{group['parser_indices']}"
        )

        print(
            f"  source_indices="
            f"{group['source_indices']}"
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
    print("-" * 80)

    for number in page_result[
        "formula_numbers"
    ]:

        print(
            f"number={number['number']} "
            f"parser_index="
            f"{number['number_parser_index']} "
            f"source_index="
            f"{number['number_source_index']}"
        )

        print(
            f"  bbox="
            f"{number['number_container_bbox']}"
        )

        print(
            f"  estimated="
            f"{number['number_estimated_bbox']}"
        )

        print(
            f"  text="
            f"{number['text']!r}"
        )

        print()

    print("Formula relations:")
    print("-" * 80)

    for relation in page_result[
        "formula_relations"
    ]:

        print(
            f"group="
            f"{relation['group_id']} "
            f"number="
            f"{relation['number']} "
            f"score="
            f"{relation['score']}"
        )

    print()


# =====================================================================
# MAIN PARSER
# =====================================================================

def parse_document(
    source_path: Path,
    output_path: Path,
) -> None:

    print("=" * 80)
    print(
        f"VKS Expert AI — "
        f"Semantic PDF Parser v{VERSION}"
    )
    print("=" * 80)
    print()

    print(
        f"Источник:\n{source_path}"
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

            debug_result = page_result

    # -----------------------------------------------------------------
    # Statistics
    # -----------------------------------------------------------------

    statistics = build_statistics(
        semantic_pages,
        validation_errors,
    )

    # -----------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------

    result = {
        "parser": {
            "name":
                "VKS Expert AI "
                "Semantic PDF Parser",

            "version":
                VERSION,
        },

        "source":
            str(
                source_path
            ),

        "statistics":
            statistics,

        "pages":
            semantic_pages,

        "validation": {
            "valid":
                len(
                    validation_errors
                ) == 0,

            "errors":
                validation_errors,
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

    # -----------------------------------------------------------------
    # Debug
    # -----------------------------------------------------------------

    if debug_result is not None:

        debug_page(
            DEBUG_PAGE,
            debug_result,
        )

    # -----------------------------------------------------------------
    # Final output
    # -----------------------------------------------------------------

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)
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

    print("-" * 80)

    labels = [
        (
            "Страниц",
            "pages",
        ),
        (
            "Элементов",
            "elements",
        ),
        (
            "Изображений",
            "images",
        ),
        (
            "Символов",
            "symbols",
        ),
        (
            "Фрагментов формул",
            "formula_fragments",
        ),
        (
            "Кандидатов схем",
            "diagram_candidates",
        ),
        (
            "Кандидатов формул",
            "formula_candidates",
        ),
        (
            "Групп формул",
            "formula_groups",
        ),
        (
            "Составных групп",
            "composite_groups",
        ),
        (
            "Номеров формул",
            "formula_numbers",
        ),
        (
            "Связанных формул",
            "formula_relations",
        ),
        (
            "Формул без номера",
            "formulas_without_number",
        ),
        (
            "Ошибок валидации",
            "validation_errors",
        ),
    ]

    for label, key in labels:

        print(
            f"{label + ':':<30}"
            f"{statistics[key]:>10}"
        )

    print()

    if validation_errors:

        print(
            "ПЕРВЫЕ ОШИБКИ ВАЛИДАЦИИ"
        )

        print("-" * 80)

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
