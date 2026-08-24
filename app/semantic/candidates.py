"""
VKS Expert AI — formula candidate detection.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .elements import (
    get_element_xref,
    get_parser_index,
    get_source_index,
)

from .elements import is_image_element

from .geometry import (
    bbox_center,
    bbox_area,
    bbox_height,
    bbox_width,
    horizontal_region,
)


def is_formula_candidate(
    element: Dict[str, Any],
) -> bool:

    return element.get("semantic_role") in {
        "formula_fragment",
        "formula_candidate",
    }


def detect_formula_candidates(
    elements: List[Dict[str, Any]],
    page_number: int,
) -> List[Dict[str, Any]]:

    candidates = []

    for element in elements:

        if not is_image_element(element):
            continue

        if not is_formula_candidate(element):
            continue

        parser_index = get_parser_index(element)

        if parser_index is None:
            continue

        xref = get_element_xref(element)

        bbox = element.get("bbox")

        geometry = element.get(
            "geometry",
            {},
        )

        role = element.get(
            "semantic_role"
        )

        confidence = float(
            element.get(
                "classification_confidence",
                0.0,
            )
        )

        formula_id = (
            f"SP30.13330"
            f"_p{page_number}"
            f"_e{parser_index}"
            f"_x"
            f"{xref if xref is not None else 'none'}"
        )

        candidates.append(
            {
                "formula_id": formula_id,
                "parser_index": parser_index,
                "source_index": get_source_index(element),
                "xref": xref,
                "bbox": bbox,
                "role": role,
                "detection_reason": element.get(
                    "classification_reason"
                ),
                "confidence": round(confidence, 3),
                "area": geometry.get("area", 0),
                "width": geometry.get("width", 0),
                "height": geometry.get("height", 0),
                "horizontal_region": geometry.get(
                    "horizontal_region"
                ),
            }
        )

    return candidates
