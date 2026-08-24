"""
VKS Expert AI — formula number detection.

v0.8
----

Поиск номеров формул вида:

    (1)
    (12)
    (123)

в текстовых элементах PDF.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .elements import (
    get_element_xref,
    get_parser_index,
    get_source_index,
    get_text,
    is_text_element,
    normalize_text,
)

from .geometry import safe_float


# ============================================================================
# REGEX
# ============================================================================


FORMULA_NUMBER_RE = re.compile(
    r"(?<!\d)\(\s*(\d{1,4})\s*\)(?!\d)"
)


# ============================================================================
# NUMBER EXTRACTION
# ============================================================================


def extract_formula_number(
    text: str,
) -> Optional[int]:
    """
    Извлекает номер формулы из текста.

    Примеры:

        "(1)"            -> 1
        ", (12)"         -> 12
        "формула (123)"  -> 123
        "текст"          -> None
    """

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


# ============================================================================
# BBOX ESTIMATION
# ============================================================================


def estimate_number_bbox(
    text_bbox: List[float],
    text: str,
) -> Optional[List[float]]:
    """
    Приблизительно определяет bbox номера формулы
    внутри bbox текстового элемента.
    """

    if not text_bbox:
        return None

    match = FORMULA_NUMBER_RE.search(
        text
    )

    if not match:
        return None

    if len(text_bbox) < 4:
        return None

    try:

        x0, y0, x1, y1 = map(
            safe_float,
            text_bbox[:4],
        )

    except Exception:
        return None

    if x1 <= x0:
        return None

    # ------------------------------------------------------------------
    # Номер находится в самом конце строки.
    #
    # Это типичная ситуация для нормативных документов:
    #
    #       ... формула ...                 (1)
    # ------------------------------------------------------------------

    suffix = text[
        match.end():
    ].strip()

    if not suffix:

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

    # ------------------------------------------------------------------
    # Если после номера есть текст,
    # используем пропорцию длины строки.
    # ------------------------------------------------------------------

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


# ============================================================================
# DETECTION
# ============================================================================


def detect_formula_numbers(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Находит номера формул среди элементов страницы.
    """

    numbers: List[Dict[str, Any]] = []

    for element in elements:

        if not is_text_element(element):
            continue

        text = get_text(element)

        number = extract_formula_number(
            text
        )

        if number is None:
            continue

        # --------------------------------------------------------------
        # Идентификаторы
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Geometry
        # --------------------------------------------------------------

        bbox = element.get(
            "bbox"
        )

        estimated_bbox = (
            estimate_number_bbox(
                bbox,
                text,
            )
            if isinstance(
                bbox,
                list,
            )
            else None
        )

        # --------------------------------------------------------------
        # Text analysis
        # --------------------------------------------------------------

        normalized = normalize_text(
            text
        )

        match = FORMULA_NUMBER_RE.search(
            text
        )

        if match:

            prefix = normalize_text(
                text[
                    :match.start()
                ]
            )

            suffix = normalize_text(
                text[
                    match.end():
                ]
            )

        else:

            prefix = ""
            suffix = ""

        # --------------------------------------------------------------
        # Confidence
        # --------------------------------------------------------------

        confidence = 0.0

        # Номер находится в конце строки.
        if not suffix:
            confidence += 50.0

        # Перед номером стоит запятая.
        if prefix.endswith(","):
            confidence += 20.0

        # Очень короткий текстовый элемент.
        if len(normalized) <= 12:
            confidence += 20.0

        # Элемент практически полностью состоит
        # из номера формулы.
        if re.fullmatch(
            r"[,\s]*\(\s*\d{1,4}\s*\)",
            normalized,
        ):
            confidence += 30.0

        confidence = min(
            confidence,
            100.0,
        )

        # --------------------------------------------------------------
        # Result
        # --------------------------------------------------------------

        numbers.append(
            {
                "number": number,

                "number_parser_index":
                    parser_index,

                "number_source_index":
                    source_index,

                "number_xref":
                    xref,

                "number_container_bbox":
                    bbox,

                "number_estimated_bbox":
                    estimated_bbox,

                "text":
                    text,

                "prefix":
                    prefix,

                "suffix":
                    suffix,

                "confidence":
                    round(
                        confidence,
                        3,
                    ),
            }
        )

    return numbers
