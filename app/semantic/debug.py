"""
VKS Expert AI — semantic parser debug output.
"""

from __future__ import annotations

from typing import Any, Dict

from .elements import (
    get_element_xref,
    get_parser_index,
    get_source_index,
    get_text,
    is_text_element,
    normalize_text,
)


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
        page_result["page_geometry"],
    )

    print()

    for element in page_result["elements"]:

        parser_index = get_parser_index(element)

        source_index = get_source_index(element)

        xref = get_element_xref(element)

        element_type = element.get("type")

        bbox = element.get("bbox")

        role = element.get(
            "semantic_role",
            "",
        )

        text = ""

        if is_text_element(element):

            text = normalize_text(
                get_text(element)
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

    for group in page_result["formula_groups"]:

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

    for number in page_result["formula_numbers"]:

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

    for relation in page_result["formula_relations"]:

        print(
            f"group="
            f"{relation['group_id']} "
            f"number="
            f"{relation['number']} "
            f"score="
            f"{relation['score']}"
        )

    print()
    