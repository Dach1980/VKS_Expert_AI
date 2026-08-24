"""
Contextual semantic refinement.

Уточнение классификации image-элементов
на основе контекста страницы.

На этом этапе используется только геометрия
и уже обнаруженные номера формул.

OCR и распознавание содержания изображения
здесь не выполняются.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .config import (
    FORMULA_NUMBER_MAX_X_DISTANCE,
    FORMULA_NUMBER_Y_TOLERANCE,
)

from .geometry import (
    bbox_center,
    safe_float,
)


def _bbox_overlap_y(
    bbox_a: List[float],
    bbox_b: List[float],
) -> float:
    """
    Возвращает вертикальное пересечение bbox.

    Если bbox не пересекаются по Y,
    возвращается положительное расстояние
    между ними.

    Возвращаемое значение:

        > 0  -> bbox разделены по Y
        = 0  -> bbox соприкасаются
        < 0  -> bbox пересекаются по Y
    """

    ay0, ay1 = (
        safe_float(bbox_a[1]),
        safe_float(bbox_a[3]),
    )

    by0, by1 = (
        safe_float(bbox_b[1]),
        safe_float(bbox_b[3]),
    )

    overlap = min(ay1, by1) - max(ay0, by0)

    if overlap >= 0:
        return -overlap

    if ay1 < by0:
        return by0 - ay1

    return ay0 - by1


def _is_formula_number_near_image(
    image: Dict[str, Any],
    number: Dict[str, Any],
) -> bool:
    """
    Проверяет, расположен ли номер формулы
    справа от изображения и достаточно близко
    по вертикали и горизонтали.
    """

    image_bbox = image.get("bbox")

    number_bbox = (
        number.get("number_estimated_bbox")
        or number.get("number_container_bbox")
    )

    if not image_bbox or not number_bbox:
        return False

    if len(image_bbox) < 4 or len(number_bbox) < 4:
        return False

    ix0, iy0, ix1, iy1 = map(
        safe_float,
        image_bbox[:4],
    )

    nx0, ny0, nx1, ny1 = map(
        safe_float,
        number_bbox[:4],
    )

    # --------------------------------------------------------------
    # Номер должен находиться справа от изображения.
    #
    # Допускаем небольшое пересечение bbox,
    # но не разрешаем номер находиться
    # полностью слева.
    # --------------------------------------------------------------

    if nx1 < ix0:
        return False

    horizontal_distance = max(
        0.0,
        nx0 - ix1,
    )

    if (
        horizontal_distance
        > FORMULA_NUMBER_MAX_X_DISTANCE
    ):
        return False

    # --------------------------------------------------------------
    # Вертикальная близость.
    # --------------------------------------------------------------

    image_center_y = bbox_center(
        image_bbox
    )[1]

    number_center_y = bbox_center(
        number_bbox
    )[1]

    center_y_distance = abs(
        image_center_y
        - number_center_y
    )

    vertical_gap = _bbox_overlap_y(
        image_bbox,
        number_bbox,
    )

    # Если bbox не пересекаются по Y,
    # проверяем фактическое расстояние.
    if (
        center_y_distance
        > FORMULA_NUMBER_Y_TOLERANCE
        and vertical_gap > 0
    ):
        return False

    return True


def _formula_number_distance(
    image: Dict[str, Any],
    number: Dict[str, Any],
) -> Tuple[float, float]:
    """
    Возвращает расстояния:

        vertical_distance
        horizontal_distance

    Используется для выбора ближайшего номера
    среди нескольких подходящих кандидатов.
    """

    image_bbox = image.get("bbox")

    number_bbox = (
        number.get("number_estimated_bbox")
        or number.get("number_container_bbox")
    )

    if not image_bbox or not number_bbox:
        return (
            float("inf"),
            float("inf"),
        )

    image_center_y = bbox_center(
        image_bbox
    )[1]

    number_center_y = bbox_center(
        number_bbox
    )[1]

    ix1 = safe_float(
        image_bbox[2]
    )

    nx0 = safe_float(
        number_bbox[0]
    )

    vertical_distance = abs(
        image_center_y
        - number_center_y
    )

    horizontal_distance = max(
        0.0,
        nx0 - ix1,
    )

    return (
        vertical_distance,
        horizontal_distance,
    )


def _find_nearest_formula_number(
    image: Dict[str, Any],
    formula_numbers: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Находит ближайший допустимый номер формулы
    для изображения.

    Если подходящих номеров нет,
    возвращает None.
    """

    candidates = []

    for number in formula_numbers:

        if not _is_formula_number_near_image(
            image,
            number,
        ):
            continue

        distance = _formula_number_distance(
            image,
            number,
        )

        candidates.append(
            (
                distance,
                number,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

    return candidates[0][1]


def refine_formula_candidates(
    elements: List[Dict[str, Any]],
    formula_numbers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Выполняет контекстное уточнение semantic_role.

    Основной случай:

        diagram_candidate
            +
        близкий номер формулы справа
            ->
        formula_candidate

    Исходные элементы не изменяются:
    функция создаёт копии словарей.
    """

    if not elements:
        return []

    if not formula_numbers:
        return [
            dict(element)
            for element in elements
        ]

    refined: List[Dict[str, Any]] = []

    for element in elements:

        enriched = dict(element)

        element_type = enriched.get(
            "element_type",
            enriched.get("type"),
        )

        # ----------------------------------------------------------
        # Работаем только с image.
        # ----------------------------------------------------------

        if element_type != "image":
            refined.append(enriched)
            continue

        role = enriched.get(
            "semantic_role"
        )

        # ----------------------------------------------------------
        # Уже определённая формула
        # не требует дополнительной обработки.
        # ----------------------------------------------------------

        if role in {
            "formula_fragment",
            "formula_candidate",
        }:
            refined.append(enriched)
            continue

        # ----------------------------------------------------------
        # Контекстная коррекция нужна прежде всего
        # для крупных изображений, которые первичный
        # классификатор определил как diagram_candidate.
        # ----------------------------------------------------------

        if role != "diagram_candidate":
            refined.append(enriched)
            continue

        matched_number = _find_nearest_formula_number(
            enriched,
            formula_numbers,
        )

        if matched_number is not None:

            enriched[
                "semantic_role"
            ] = "formula_candidate"

            enriched[
                "classification_reason"
            ] = "formula_number_context"

            original_confidence = safe_float(
                enriched.get(
                    "classification_confidence",
                    0.0,
                )
            )

            enriched[
                "classification_confidence"
            ] = round(
                max(
                    original_confidence,
                    0.80,
                ),
                3,
            )

            enriched[
                "classification_context"
            ] = {
                "formula_number": matched_number.get(
                    "number"
                ),
                "formula_number_parser_index": (
                    matched_number.get(
                        "number_parser_index"
                    )
                ),
            }

        refined.append(enriched)

    return refined
