"""
VKS Expert AI — semantic result validation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .elements import get_parser_index


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
        get_parser_index(element)
        for element in elements
    }

    for element in elements:

        index = get_parser_index(element)

        if not isinstance(index, int):

            errors.append(
                "element without valid parser_index"
            )

    for candidate in candidates:

        index = candidate.get(
            "parser_index"
        )

        if index not in element_indices:

            errors.append(
                "formula candidate points to unknown "
                "parser_index"
            )

    group_ids = set()

    for group in groups:

        group_id = group.get("group_id")

        if group_id in group_ids:

            errors.append(
                f"duplicate group_id {group_id}"
            )

        group_ids.add(group_id)

        for index in group.get(
            "parser_indices",
            [],
        ):

            if index not in element_indices:

                errors.append(
                    "formula group contains unknown "
                    "parser_index"
                )

    valid_group_ids = {
        group.get("group_id")
        for group in groups
    }

    for formula in formulas:

        group_id = formula.get("group_id")

        if group_id not in valid_group_ids:

            errors.append(
                "formula points to unknown group"
            )

    for relation in relations:

        group_id = relation.get("group_id")

        if group_id not in valid_group_ids:

            errors.append(
                "relation points to unknown group"
            )

    return errors
