"""
Formula candidate detection.

VKS Expert AI — Semantic Parser.

Модуль формирует структурированные записи
кандидатов формул из уже классифицированных
image-элементов.

Важно:
    Этот модуль НЕ выполняет OCR и не определяет
    содержимое изображения.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .elements import (
    get_element_xref,
    get_parser_index,
    get_source_index,
)

from .geometry import (
    bbox_area,
    bbox_height,
    bbox_width,
)


# ============================================================================
# FORMULA CANDIDATE CHECK
# ============================================================================


def is_formula_candidate(
    element: Dict[str, Any],
) -> bool:
    """
    Проверяет, является ли элемент кандидатом формулы.

    Кандидатами считаются:

        formula_fragment
        formula_candidate

    Контекстная классификация также приводит
    diagram_candidate -> formula_candidate,
    поэтому отдельная обработка здесь не требуется.
    """

    return element.get(
        "semantic_role"
    ) in {
        "formula_fragment",
        "formula_candidate",
    }


# ============================================================================
# GEOMETRY
# ============================================================================


def _get_candidate_geometry(
    element: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Возвращает геометрию элемента.

    Приоритет:

        1. element["geometry"]
        2. уже рассчитанные поля:
           bbox_area
           bbox_width
           bbox_height
        3. непосредственный расчёт из bbox

    Это важно для элементов, которые были
    классифицированы контекстно.

    В некоторых версиях pipeline поле geometry
    может отсутствовать, хотя bbox и производные
    геометрические параметры уже существуют.
    """

    bbox = element.get(
        "bbox"
    )

    geometry = element.get(
        "geometry"
    )

    if not isinstance(
        geometry,
        dict,
    ):
        geometry = {}

    # ------------------------------------------------------------------
    # AREA
    # ------------------------------------------------------------------

    area = geometry.get(
        "area"
    )

    if area is None:

        area = element.get(
            "bbox_area"
        )

    if area is None:

        area = bbox_area(
            bbox
        )

    # ------------------------------------------------------------------
    # WIDTH
    # ------------------------------------------------------------------

    width = geometry.get(
        "width"
    )

    if width is None:

        width = element.get(
            "bbox_width"
        )

    if width is None:

        width = bbox_width(
            bbox
        )

    # ------------------------------------------------------------------
    # HEIGHT
    # ------------------------------------------------------------------

    height = geometry.get(
        "height"
    )

    if height is None:

        height = element.get(
            "bbox_height"
        )

    if height is None:

        height = bbox_height(
            bbox
        )

    # ------------------------------------------------------------------
    # HORIZONTAL REGION
    # ------------------------------------------------------------------

    horizontal_region = geometry.get(
        "horizontal_region"
    )

    # Если enrich_element уже вычислил
    # horizontal_region, используем его.
    if horizontal_region is None:

        horizontal_region = element.get(
            "horizontal_region"
        )

    return {
        "area": area or 0,
        "width": width or 0,
        "height": height or 0,
        "horizontal_region": horizontal_region,
    }


# ============================================================================
# DETECTION
# ============================================================================


def detect_formula_candidates(
    elements: List[Dict[str, Any]],
    page_number: int,
) -> List[Dict[str, Any]]:
    """
    Формирует список кандидатов формул.

    На входе находятся уже классифицированные
    элементы страницы.

    Функция не выполняет повторную классификацию.

    Для каждого кандидата сохраняются:

        formula_id
        parser_index
        source_index
        xref
        bbox
        role
        detection_reason
        confidence
        area
        width
        height
        horizontal_region
    """

    candidates: List[
        Dict[str, Any]
    ] = []

    for element in elements:

        # ------------------------------------------------------------------
        # Проверяем semantic_role
        # ------------------------------------------------------------------

        if not is_formula_candidate(
            element
        ):
            continue

        # ------------------------------------------------------------------
        # IDENTIFIERS
        # ------------------------------------------------------------------

        parser_index = get_parser_index(
            element
        )

        if parser_index is None:
            continue

        xref = get_element_xref(
            element
        )

        source_index = get_source_index(
            element
        )

        bbox = element.get(
            "bbox"
        )

        # ------------------------------------------------------------------
        # GEOMETRY
        # ------------------------------------------------------------------

        geometry = _get_candidate_geometry(
            element
        )

        role = element.get(
            "semantic_role"
        )

        confidence = float(
            element.get(
                "classification_confidence",
                0.0,
            )
            or 0.0
        )

        # ------------------------------------------------------------------
        # FORMULA ID
        # ------------------------------------------------------------------

        formula_id = (
            f"SP30.13330"
            f"_p{page_number}"
            f"_e{parser_index}"
            f"_x"
            f"{xref if xref is not None else 'none'}"
        )

        # ------------------------------------------------------------------
        # RESULT
        # ------------------------------------------------------------------

        candidates.append(
            {
                "formula_id": formula_id,

                "parser_index": parser_index,

                "source_index": source_index,

                "xref": xref,

                "bbox": bbox,

                "role": role,

                "detection_reason": element.get(
                    "classification_reason"
                ),

                "confidence": round(
                    confidence,
                    3,
                ),

                "area": geometry.get(
                    "area",
                    0,
                ),

                "width": geometry.get(
                    "width",
                    0,
                ),

                "height": geometry.get(
                    "height",
                    0,
                ),

                "horizontal_region": geometry.get(
                    "horizontal_region"
                ),
            }
        )

    return candidates
