"""
VKS Expert AI — Semantic Parser Pipeline v0.8.1.

Pipeline отвечает только за последовательность операций.
Алгоритмы анализа находятся в специализированных модулях.

v0.8.1
------

Изменения относительно v0.8:

    • добавлен этап page-relative geometry;
    • для элементов рассчитывается horizontal_region;
    • используется уже определённая page_geometry["width"];
    • логика formula ↔ number не изменена;
    • elements.py остаётся независимым от других semantic-модулей.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .candidates import (
    detect_formula_candidates,
)

from .classification import (
    classify_image,
)

from .context import (
    enrich_formula_context,
)

from .contextual_classification import (
    refine_formula_candidates,
)

from .elements import (
    normalize_page_elements,
    enrich_element,
)

from .formula_linking import (
    link_formula_numbers,
)

from .formula_numbers import (
    detect_formula_numbers,
)

from .geometry import (
    detect_page_geometry,
    horizontal_region,
)

from .grouping import (
    build_formula_groups,
)

from .validation import (
    validate_page_result,
)


# ============================================================================
# ELEMENT CLASSIFICATION
# ============================================================================


def classify_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Выполняет semantic-классификацию элементов страницы.

    В текущей версии классифицируются только image-элементы.

    Для каждого изображения добавляются:

        semantic_role
        classification_reason
        classification_confidence

    Текстовые элементы не классифицируются.
    """

    classified: List[Dict[str, Any]] = []

    for element in elements:

        enriched = dict(element)

        element_type = enriched.get(
            "element_type",
            enriched.get("type"),
        )

        # ------------------------------------------------------------------
        # IMAGE
        # ------------------------------------------------------------------

        if element_type == "image":

            (
                role,
                reason,
                confidence,
            ) = classify_image(
                enriched
            )

            enriched["semantic_role"] = role

            enriched[
                "classification_reason"
            ] = reason

            enriched[
                "classification_confidence"
            ] = round(
                float(confidence),
                3,
            )

        # ------------------------------------------------------------------
        # NON-IMAGE
        # ------------------------------------------------------------------

        else:

            enriched.setdefault(
                "semantic_role",
                None,
            )

            enriched.setdefault(
                "classification_reason",
                None,
            )

            enriched.setdefault(
                "classification_confidence",
                None,
            )

        classified.append(
            enriched
        )

    return classified


# ============================================================================
# PAGE-RELATIVE GEOMETRY
# ============================================================================


def enrich_page_relative_geometry(
    elements: List[Dict[str, Any]],
    page_width: float,
) -> List[Dict[str, Any]]:
    """
    Добавляет геометрические характеристики,
    зависящие от ширины страницы.

    В частности:

        horizontal_region

    Возможные значения:

        left
        center
        right
        unknown

    Важно:

        Эта функция не изменяет исходные элементы.
        Создаются копии словарей.

    Геометрия элемента рассчитывается относительно
    ширины страницы, а не относительно других элементов.

    Логика horizontal_region находится в geometry.py.
    """

    enriched_elements: List[
        Dict[str, Any]
    ] = []

    for element in elements:

        enriched = dict(
            element
        )

        bbox = enriched.get(
            "bbox"
        )

        if (
            isinstance(
                bbox,
                (list, tuple),
            )
            and len(bbox) >= 4
            and page_width > 0
        ):

            enriched[
                "horizontal_region"
            ] = horizontal_region(
                list(bbox[:4]),
                page_width,
            )

        else:

            enriched[
                "horizontal_region"
            ] = "unknown"

        enriched_elements.append(
            enriched
        )

    return enriched_elements


# ============================================================================
# PAGE PROCESSING
# ============================================================================


def process_page(
    page: Dict[str, Any],
    page_number: int,
) -> Dict[str, Any]:
    """
    Полностью обрабатывает одну страницу.

    Порядок:

        1. normalization
        2. page geometry
        3. element enrichment
        4. image classification
        5. formula number detection
        6. contextual formula classification
        7. page-relative geometry
        8. formula candidate detection
        9. formula grouping
        10. formula-number linking
        11. formula context enrichment
    """

    raw_elements = page.get(
        "elements",
        [],
    )

    # ------------------------------------------------------------------
    # 1. NORMALIZATION
    # ------------------------------------------------------------------

    elements = normalize_page_elements(
        raw_elements
    )

    # ------------------------------------------------------------------
    # 2. PAGE GEOMETRY
    # ------------------------------------------------------------------

    page_geometry = detect_page_geometry(
        page,
        elements,
    )

    # ------------------------------------------------------------------
    # 3. ELEMENT ENRICHMENT
    # ------------------------------------------------------------------

    enriched_elements = [
        enrich_element(
            element,
        )
        for element in elements
    ]

    # ------------------------------------------------------------------
    # 4. IMAGE CLASSIFICATION
    # ------------------------------------------------------------------

    classified_elements = classify_page_elements(
        enriched_elements
    )

    # ------------------------------------------------------------------
    # 5. FORMULA NUMBERS
    # ------------------------------------------------------------------

    numbers = detect_formula_numbers(
        classified_elements
    )

    # ------------------------------------------------------------------
    # 6. CONTEXTUAL FORMULA CLASSIFICATION
    # ------------------------------------------------------------------

    classified_elements = refine_formula_candidates(
        classified_elements,
        numbers,
    )

    # ------------------------------------------------------------------
    # 7. PAGE-RELATIVE GEOMETRY
    # ------------------------------------------------------------------

    classified_elements = (
        enrich_page_relative_geometry(
            classified_elements,
            page_geometry.get(
                "width",
                0.0,
            ),
        )
    )

    # ------------------------------------------------------------------
    # 8. FORMULA CANDIDATES
    # ------------------------------------------------------------------

    candidates = detect_formula_candidates(
        classified_elements,
        page_number,
    )

    # ------------------------------------------------------------------
    # 9. FORMULA GROUPS
    # ------------------------------------------------------------------

    groups = build_formula_groups(
        candidates
    )

    # ------------------------------------------------------------------
    # 10. LINK FORMULAS ↔ NUMBERS
    # ------------------------------------------------------------------

    (
        formula_records,
        relations,
    ) = link_formula_numbers(
        groups,
        numbers,
    )

    # ------------------------------------------------------------------
    # 11. FORMULA CONTEXT
    # ------------------------------------------------------------------

    enrich_formula_context(
        formula_records,
        classified_elements,
    )

    return {
        "page_number": page_number,

        "page_geometry": page_geometry,

        "elements_count": len(
            classified_elements
        ),

        "elements": classified_elements,

        "formula_candidates": candidates,

        "formula_groups": groups,

        "formula_numbers": numbers,

        "formulas": formula_records,

        "formula_relations": relations,
    }


# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================


def process_document_pages(
    pages: List[Dict[str, Any]],
) -> tuple[
    List[Dict[str, Any]],
    List[str],
]:
    """
    Обрабатывает весь документ постранично.

    Возвращает:

        semantic_pages
        validation_errors
    """

    semantic_pages: List[
        Dict[str, Any]
    ] = []

    validation_errors: List[str] = []

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

    return (
        semantic_pages,
        validation_errors,
    )
