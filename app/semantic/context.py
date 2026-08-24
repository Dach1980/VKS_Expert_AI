"""
Context extraction around formulas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .elements import (
    get_parser_index,
    get_text,
    is_text_element,
    normalize_text,
)


def find_previous_text_element(
    elements: List[Dict[str, Any]],
    parser_index: int,
) -> Optional[Dict[str, Any]]:
    for element in reversed(elements):
        index = get_parser_index(element)

        if index is None:
            continue

        if index >= parser_index:
            continue

        if is_text_element(element):
            text = normalize_text(
                get_text(element)
            )

            if text:
                return element

    return None


def find_next_text_element(
    elements: List[Dict[str, Any]],
    parser_index: int,
) -> Optional[Dict[str, Any]]:
    for element in elements:
        index = get_parser_index(element)

        if index is None:
            continue

        if index <= parser_index:
            continue

        if is_text_element(element):
            text = normalize_text(
                get_text(element)
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

        first_index = min(indices)
        last_index = max(indices)

        previous = find_previous_text_element(
            elements,
            first_index,
        )

        following = find_next_text_element(
            elements,
            last_index,
        )

        formula["previous_text"] = (
            normalize_text(
                get_text(previous)
            )
            if previous
            else None
        )

        formula["previous_text_parser_index"] = (
            get_parser_index(previous)
            if previous
            else None
        )

        formula["next_text"] = (
            normalize_text(
                get_text(following)
            )
            if following
            else None
        )

        formula["next_text_parser_index"] = (
            get_parser_index(following)
            if following
            else None
        )
        