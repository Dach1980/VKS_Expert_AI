"""
VKS Expert AI — image classification.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .config import (
    DIAGRAM_MIN_AREA,
    FORMULA_CANDIDATE_MIN_AREA,
    FORMULA_FRAGMENT_MIN_AREA,
    SMALL_MATH_MAX_HEIGHT,
    SMALL_MATH_MAX_WIDTH,
    SYMBOL_MAX_AREA,
)

from .geometry import (
    bbox_area,
    bbox_height,
    bbox_width,
)


def classify_image(
    element: Dict[str, Any],
) -> Tuple[str, str, float]:

    bbox = element.get("bbox")

    area = bbox_area(bbox)

    width = bbox_width(bbox)

    height = bbox_height(bbox)

    if area <= 0:
        return (
            "unknown",
            "invalid_geometry",
            0.0,
        )

    if area >= DIAGRAM_MIN_AREA:

        if height > 0:

            aspect_ratio = width / height

            if aspect_ratio >= 8.0:

                return (
                    "diagram_candidate",
                    "large_extreme_aspect_ratio",
                    0.75,
                )

        return (
            "diagram_candidate",
            "large_image",
            0.70,
        )

    if area <= SYMBOL_MAX_AREA:

        if (
            width <= SMALL_MATH_MAX_WIDTH
            and height <= SMALL_MATH_MAX_HEIGHT
            and area >= FORMULA_FRAGMENT_MIN_AREA
        ):

            return (
                "formula_fragment",
                "small_math_geometry",
                0.75,
            )

        return (
            "symbol",
            "small_image",
            0.80,
        )

    if area >= FORMULA_CANDIDATE_MIN_AREA:

        if height > 0:

            aspect_ratio = width / height

            if aspect_ratio >= 8.0:

                return (
                    "diagram_candidate",
                    "medium_extreme_aspect_ratio",
                    0.55,
                )

        return (
            "formula_candidate",
            "medium_math_geometry",
            0.65,
        )

    return (
        "unknown",
        "unclassified",
        0.20,
    )
