"""
VKS Expert AI — semantic parsing pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .classification import classify_image
from .context import enrich_formula_context
from .elements import (
    get_text,
    is_image_element,
    is_text_element,
    normalize_page_elements,
    normalize_text,
    element_identity,
)

from .formula_linking import link_formula_numbers
from .formula_numbers import extract_formula_number
from .formula_numbers import detect_formula_numbers

from .candidates import detect_formula_candidates
from .grouping import build_formula_groups

from .geometry import (
    bbox_area,
    bbox_center,
    bbox_height,
    bbox_width,
    horizontal_region,
    safe_float,
)

from .source import get_pages


def detect_page_geometry(
    page: Dict[str, Any],
    elements: List[Dict[str, Any]],
) -> Dict[str, float]:

    page_width = safe_float(
        page.get("width")
    )

    page_height = safe_float(
        page.get("height")
    )

    if page_width <= 0:

        page_width = max(
            (
                safe_float(
                    element.get("bbox")[2]
                )
                for element in elements
                if element.get("bbox")
                and len(element.get("bbox")) >= 4
            ),
            default=0.0,
        )

    if page_height <= 0:

        page_height = max(
            (
                safe_float(
                    element.get("bbox")[3]
                )
                for element in elements
                if element.get("bbox")
                and len(element.get("bbox")) >= 4
            ),
            default=0.0,
        )

    return {
        "width": round(page_width, 3),
        "height": round(page_height, 3),
    }


def enrich_element(
    element: Dict[str, Any],
    page_geometry: Dict[str, float],
) -> Dict[str, Any]:

    result = dict(element)

    bbox = element.get("bbox")

    result["identity"] = element_identity(
        element
    )

    if is_image_element(element):

        area = bbox_area(bbox)

        width = bbox_width(bbox)

        height = bbox_height(bbox)

        center = bbox_center(bbox)

        result["geometry"] = {
            "width": round(width, 3),

            "height": round(height, 3),

            "area": round(area, 3),

            "center": [
                round(center[0], 3),
                round(center[1], 3),
            ],

            "horizontal_region":
                horizontal_region(
                    bbox,
                    page_geometry["width"],
                ),
        }

        (
            role,
            reason,
            confidence,
        ) = classify_image(element)

        result["semantic_role"] = role

        result["classification_reason"] = reason

        result["classification_confidence"] = confidence

    elif is_text_element(element):

        text = normalize_text(
            get_text(element)
        )

        result["text_normalized"] = text

        number = extract_formula_number(text)

        if number is not None:

            result["semantic_role"] = (
                "formula_number"
            )

        else:

            result["semantic_role"] = "text"

    return result


def process_page(
    page: Dict[str, Any],
    page_number: int,
) -> Dict[str, Any]:

    raw_elements = page.get(
        "elements",
        [],
    )

    elements = normalize_page_elements(
        raw_elements
    )

    page_geometry = detect_page_geometry(
        page,
        elements,
    )

    enriched_elements = [
        enrich_element(
            element,
            page_geometry,
        )
        for element in elements
    ]

    candidates = detect_formula_candidates(
        enriched_elements,
        page_number,
    )

    groups = build_formula_groups(
        candidates
    )

    numbers = detect_formula_numbers(
        enriched_elements
    )

    formula_records, relations = (
        link_formula_numbers(
            groups,
            numbers,
        )
    )

    enrich_formula_context(
        formula_records,
        enriched_elements,
    )

    return {
        "page_number": page_number,

        "page_geometry": page_geometry,

        "elements_count": len(
            enriched_elements
        ),

        "elements": enriched_elements,

        "formula_candidates": candidates,

        "formula_groups": groups,

        "formula_numbers": numbers,

        "formulas": formula_records,

        "formula_relations": relations,
    }
