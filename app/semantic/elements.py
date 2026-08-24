"""
VKS Expert AI — element utilities.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def get_source_index(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get("source_index")

    if isinstance(value, int):
        return value

    return None


def get_parser_index(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get("parser_index")

    if isinstance(value, int):
        return value

    return None


def get_element_xref(
    element: Dict[str, Any],
) -> Optional[int]:

    value = element.get("xref")

    if isinstance(value, int):
        return value

    try:
        if value is not None:
            return int(value)

    except (TypeError, ValueError):
        pass

    return None


def element_identity(
    element: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "parser_index": get_parser_index(element),
        "source_index": get_source_index(element),
        "xref": get_element_xref(element),
    }


def normalize_page_elements(
    elements: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    normalized = []

    for position, original in enumerate(elements):

        if not isinstance(original, dict):
            continue

        element = dict(original)

        original_index = element.get("index")

        if isinstance(original_index, int):
            element["source_index"] = original_index
        else:
            element["source_index"] = None

        element["parser_index"] = position

        normalized.append(element)

    return normalized


def is_text_element(
    element: Dict[str, Any],
) -> bool:

    return element.get("type") == "text"


def is_image_element(
    element: Dict[str, Any],
) -> bool:

    return element.get("type") == "image"


def get_text(
    element: Dict[str, Any],
) -> str:

    value = element.get("text")

    if value is None:
        value = element.get("content")

    if value is None:
        return ""

    return str(value)


def normalize_text(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text.replace("\n", " "),
    ).strip()
