"""
VKS Expert AI — element utilities.

v0.8
----

Нижнеуровневый модуль работы с элементами PDF.

Архитектурное правило:

    elements.py
        ↓
    не импортирует другие semantic-модули

Это позволяет избежать циклических импортов.

Основные обязанности:

    • идентификация элементов;
    • нормализация индексов;
    • работа с типами элементов;
    • извлечение текста;
    • нормализация текста;
    • работа с bbox;
    • вычисление геометрических характеристик;
    • обогащение элементов semantic-полями.
"""

from __future__ import annotations

import re

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

# ============================================================================
# INDEX / IDENTITY
# ============================================================================


def get_source_index(
    element: Dict[str, Any],
) -> Optional[int]:
    """
    Возвращает исходный индекс элемента.

    В исходном elements.json обычно используется:

        index

    После нормализации:

        source_index
    """

    value = element.get(
        "source_index"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    return None


def get_parser_index(
    element: Dict[str, Any],
) -> Optional[int]:
    """
    Возвращает parser_index элемента.

    parser_index — это позиция элемента
    внутри нормализованного списка страницы.
    """

    value = element.get(
        "parser_index"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    return None


def get_element_xref(
    element: Dict[str, Any],
) -> Optional[int]:
    """
    Возвращает PDF xref элемента.

    Поддерживаются:

        int
        строковое представление числа
    """

    value = element.get(
        "xref"
    )

    if isinstance(
        value,
        int,
    ):
        return value

    try:

        if value is not None:
            return int(value)

    except (
        TypeError,
        ValueError,
    ):
        pass

    return None


def element_identity(
    element: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Возвращает компактную идентичность элемента.
    """

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


# ============================================================================
# NORMALIZATION
# ============================================================================


def normalize_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Нормализует элементы одной страницы.

    Исходное:

        index

    сохраняется как:

        source_index

    Дополнительно назначается:

        parser_index

    parser_index всегда соответствует позиции
    элемента в результирующем списке.
    """

    normalized: List[
        Dict[str, Any]
    ] = []

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

        # --------------------------------------------------------------
        # SOURCE INDEX
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # PARSER INDEX
        # --------------------------------------------------------------

        element[
            "parser_index"
        ] = position

        normalized.append(
            element
        )

    return normalized


# ============================================================================
# ELEMENT TYPE
# ============================================================================


def get_element_type(
    element: Dict[str, Any],
) -> Optional[str]:
    """
    Возвращает тип элемента.
    """

    value = element.get(
        "type"
    )

    if value is None:
        return None

    return str(
        value
    )


def is_text_element(
    element: Dict[str, Any],
) -> bool:
    """
    Проверяет, является ли элемент текстом.
    """

    return (
        get_element_type(
            element
        )
        == "text"
    )


def is_image_element(
    element: Dict[str, Any],
) -> bool:
    """
    Проверяет, является ли элемент изображением.
    """

    return (
        get_element_type(
            element
        )
        == "image"
    )


def is_formula_element(
    element: Dict[str, Any],
) -> bool:
    """
    Проверяет, относится ли image-элемент
    к формуле.
    """

    if not is_image_element(
        element
    ):
        return False

    role = str(
        element.get(
            "role",
            "",
        )
    ).lower()

    return role in {
        "formula_fragment",
        "formula_candidate",
        "formula",
        "symbol",
    }


# ============================================================================
# TEXT
# ============================================================================


def get_text(
    element: Dict[str, Any],
) -> str:
    """
    Извлекает текст элемента.

    Поддерживаются:

        text
        content
    """

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
    """
    Нормализует пробелы и переносы строк.
    """

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text.replace(
            "\n",
            " ",
        ),
    ).strip()


# ============================================================================
# GEOMETRY
# ============================================================================


def get_bbox(
    element: Dict[str, Any],
) -> Optional[List[float]]:
    """
    Возвращает bbox:

        [x0, y0, x1, y1]

    При некорректном bbox возвращает None.
    """

    bbox = element.get(
        "bbox"
    )

    if not isinstance(
        bbox,
        (list, tuple),
    ):
        return None

    if len(bbox) < 4:
        return None

    result: List[
        float
    ] = []

    for value in bbox[:4]:

        try:

            result.append(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    return result


def bbox_width(
    bbox: Optional[List[float]],
) -> float:
    """
    Возвращает ширину bbox.
    """

    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        float(bbox[2])
        - float(bbox[0]),
    )


def bbox_height(
    bbox: Optional[List[float]],
) -> float:
    """
    Возвращает высоту bbox.
    """

    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        float(bbox[3])
        - float(bbox[1]),
    )


def bbox_area(
    bbox: Optional[List[float]],
) -> float:
    """
    Возвращает площадь bbox.
    """

    return (
        bbox_width(bbox)
        * bbox_height(bbox)
    )


# ============================================================================
# ENRICHMENT
# ============================================================================


def enrich_element(
    element: Dict[str, Any],
    parser_index: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Обогащает элемент вычисляемыми semantic-полями.

    ВАЖНО:

        parser_index является индексом элемента.

        page_geometry сюда НЕ передаётся.

    Функция не изменяет исходный словарь,
    а создаёт его копию.

    Добавляются:

        parser_index
        source_index
        normalized_text
        element_type
        bbox_width
        bbox_height
        bbox_area
        identity
    """

    enriched = dict(
        element
    )

    # ==================================================================
    # PARSER INDEX
    # ==================================================================

    existing_parser_index = (
        enriched.get(
            "parser_index"
        )
    )

    if isinstance(
        parser_index,
        int,
    ):

        enriched[
            "parser_index"
        ] = parser_index

    elif isinstance(
        existing_parser_index,
        int,
    ):

        # Нормальный случай после
        # normalize_page_elements().
        #
        # Сохраняем существующий индекс.

        enriched[
            "parser_index"
        ] = existing_parser_index

    else:

        enriched[
            "parser_index"
        ] = None

    # ==================================================================
    # SOURCE INDEX
    # ==================================================================

    existing_source_index = (
        enriched.get(
            "source_index"
        )
    )

    if isinstance(
        existing_source_index,
        int,
    ):

        enriched[
            "source_index"
        ] = existing_source_index

    else:

        original_index = (
            enriched.get(
                "index"
            )
        )

        if isinstance(
            original_index,
            int,
        ):

            enriched[
                "source_index"
            ] = original_index

        else:

            enriched[
                "source_index"
            ] = None

    # ==================================================================
    # TEXT
    # ==================================================================

    text = get_text(
        enriched
    )

    enriched[
        "normalized_text"
    ] = normalize_text(
        text
    )

    # ==================================================================
    # TYPE
    # ==================================================================

    enriched[
        "element_type"
    ] = get_element_type(
        enriched
    )

    # ==================================================================
    # BBOX
    # ==================================================================

    bbox = get_bbox(
        enriched
    )

    if bbox is not None:

        enriched[
            "bbox_width"
        ] = round(
            bbox_width(bbox),
            3,
        )

        enriched[
            "bbox_height"
        ] = round(
            bbox_height(bbox),
            3,
        )

        enriched[
            "bbox_area"
        ] = round(
            bbox_area(bbox),
            3,
        )

    else:

        enriched[
            "bbox_width"
        ] = 0.0

        enriched[
            "bbox_height"
        ] = 0.0

        enriched[
            "bbox_area"
        ] = 0.0

    # ==================================================================
    # IDENTITY
    # ==================================================================

    enriched[
        "identity"
    ] = element_identity(
        enriched
    )

    return enriched


# ============================================================================
# PAGE ENRICHMENT
# ============================================================================


def enrich_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Полностью нормализует и обогащает
    элементы одной страницы.

    Это удобный высокоуровневый helper.

    Основной pipeline может использовать
    normalize_page_elements() + enrich_element()
    отдельно.
    """

    normalized = (
        normalize_page_elements(
            elements
        )
    )

    return [
        enrich_element(
            element
        )
        for element in normalized
    ]
