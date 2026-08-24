"""
Statistics for semantic parsing.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .elements import is_image_element


def build_statistics(
    pages: List[Dict[str, Any]],
    validation_errors: List[str],
) -> Dict[str, Any]:
    pages_count = len(pages)

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
        if is_image_element(element)
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
                [],
            )
            if group.get("composite")
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
                [],
            )
            if formula.get("number") is None
        )
        for page in pages
    )

    return {
        "pages": pages_count,
        "elements": elements_count,
        "images": images_count,
        "symbols": symbols_count,
        "formula_fragments": (
            formula_fragments_count
        ),
        "diagram_candidates": (
            diagram_candidates_count
        ),
        "formula_candidates": (
            formula_candidates_count
        ),
        "formula_groups": formula_groups_count,
        "composite_groups": composite_groups_count,
        "formula_numbers": formula_numbers_count,
        "formula_relations": relations_count,
        "formulas_without_number": (
            formulas_without_number
        ),
        "validation_errors": len(
            validation_errors
        ),
    }
