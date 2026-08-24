"""
VKS Expert AI — semantic debug utilities.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _format_index(value: Any, width: int = 4) -> str:
    """
    Безопасно форматирует индекс.

    None -> "-"
    int/str -> строковое значение с выравниванием.
    """
    if value is None:
        return "-".ljust(width)

    return str(value).ljust(width)


def _format_bbox(value: Any) -> str:
    """
    Безопасно форматирует bbox.
    """
    if not isinstance(value, (list, tuple)):
        return "None"

    if len(value) < 4:
        return str(value)

    try:
        return str(
            [
                round(float(value[0]), 2),
                round(float(value[1]), 2),
                round(float(value[2]), 2),
                round(float(value[3]), 2),
            ]
        )
    except (TypeError, ValueError):
        return str(value)


def _truncate_text(
    value: Any,
    max_length: int = 120,
) -> str:
    """
    Безопасно преобразует текст в строку
    и ограничивает его длину.
    """
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\n", " ").strip()

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def _get_element_text(
    element: Dict[str, Any],
) -> str:
    """
    Получает текст элемента.
    """
    value = element.get("text")

    if value is None:
        value = element.get("content")

    if value is None:
        return ""

    return str(value)


def debug_page(
    page_number: int,
    page_result: Dict[str, Any],
) -> None:
    """
    Выводит подробную диагностику одной страницы.

    Важно:
    debug-функция не должна изменять данные
    и не должна падать из-за отсутствующих индексов.
    """

    print()
    print("=" * 80)
    print(f"ELEMENT DEBUG — PAGE {page_number}")
    print("=" * 80)
    print()

    geometry = page_result.get("page_geometry")

    print(f"Page geometry: {geometry}")
    print()

    elements = page_result.get("elements", [])

    if not isinstance(elements, list):
        print("Elements: invalid")
        return

    for position, element in enumerate(elements):

        if not isinstance(element, dict):
            print(
                f"#{position:<4} "
                f"INVALID ELEMENT: {element!r}"
            )
            continue

        parser_index = element.get("parser_index")

        source_index = element.get("source_index")

        element_type = element.get("type")

        source = element.get("source")

        xref = element.get("xref")

        role = element.get("role")

        bbox = element.get("bbox")

        text = _truncate_text(
            _get_element_text(element)
        )

        print(
            f"#{_format_index(parser_index)} "
            f"type={str(element_type):<8} "
            f"source={source!s:<8} "
            f"xref={xref!s:<6} "
            f"role={str(role):<20} "
            f"bbox={_format_bbox(bbox)} "
            f"'{text}'"
        )

    print()

    # ------------------------------------------------------------------
    # Formula groups
    # ------------------------------------------------------------------

    formula_groups = page_result.get(
        "formula_groups",
        [],
    )

    if formula_groups:
        print("=" * 80)
        print(
            f"FORMULA GROUP DEBUG — PAGE {page_number}"
        )
        print("=" * 80)
        print()

        for group_index, group in enumerate(
            formula_groups
        ):
            if not isinstance(group, dict):
                continue

            members = group.get(
                "members",
                0,
            )

            parser_indices = group.get(
                "parser_indices",
                [],
            )

            source_indices = group.get(
                "source_indices",
                [],
            )

            xrefs = group.get(
                "xrefs",
                [],
            )

            bbox = group.get(
                "bbox"
            )

            composite = group.get(
                "composite",
                False,
            )

            confidence = group.get(
                "confidence",
                0.0,
            )

            print(
                f"group={group_index} "
                f"members={members} "
                f"composite={composite} "
                f"confidence={confidence}"
            )

            print(
                f"  parser_indices={parser_indices}"
            )

            print(
                f"  source_indices={source_indices}"
            )

            print(
                f"  xrefs={xrefs}"
            )

            print(
                f"  bbox={_format_bbox(bbox)}"
            )

            print()

    # ------------------------------------------------------------------
    # Formula numbers
    # ------------------------------------------------------------------

    formula_numbers = page_result.get(
        "formula_numbers",
        [],
    )

    if formula_numbers:
        print("Formula numbers:")
        print("-" * 80)

        for item in formula_numbers:

            if not isinstance(item, dict):
                continue

            number = item.get(
                "number"
            )

            parser_index = item.get(
                "number_parser_index"
            )

            source_index = item.get(
                "number_source_index"
            )

            xref = item.get(
                "number_xref"
            )

            bbox = item.get(
                "number_container_bbox"
            )

            estimated_bbox = item.get(
                "number_estimated_bbox"
            )

            text = item.get(
                "text",
                "",
            )

            print(
                f"number={number} "
                f"parser_index={parser_index} "
                f"source_index={source_index}"
            )

            print(
                f"  xref={xref}"
            )

            print(
                f"  bbox={_format_bbox(bbox)}"
            )

            print(
                f"  estimated={_format_bbox(estimated_bbox)}"
            )

            print(
                f"  text={text!r}"
            )

            print()

    # ------------------------------------------------------------------
    # Formula relations
    # ------------------------------------------------------------------

    formula_relations = page_result.get(
        "formula_relations",
        [],
    )

    if formula_relations:
        print("Formula relations:")
        print("-" * 80)

        for relation in formula_relations:

            if not isinstance(
                relation,
                dict,
            ):
                continue

            group_id = relation.get(
                "group_id"
            )

            number = relation.get(
                "number"
            )

            score = relation.get(
                "score"
            )

            print(
                f"group_id={group_id} "
                f"number={number} "
                f"score={score}"
            )

    print()
    