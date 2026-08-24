"""
Geometry helpers.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def bbox_area(
    bbox: Optional[List[float]],
) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    x0, y0, x1, y1 = map(
        safe_float,
        bbox[:4],
    )

    return (
        max(0.0, x1 - x0)
        * max(0.0, y1 - y0)
    )


def bbox_width(
    bbox: Optional[List[float]],
) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[2])
        - safe_float(bbox[0]),
    )


def bbox_height(
    bbox: Optional[List[float]],
) -> float:
    if not bbox or len(bbox) < 4:
        return 0.0

    return max(
        0.0,
        safe_float(bbox[3])
        - safe_float(bbox[1]),
    )


def bbox_center(
    bbox: Optional[List[float]],
) -> Tuple[float, float]:
    if not bbox or len(bbox) < 4:
        return 0.0, 0.0

    x0, y0, x1, y1 = map(
        safe_float,
        bbox[:4],
    )

    return (
        (x0 + x1) / 2.0,
        (y0 + y1) / 2.0,
    )


def bbox_union(
    bboxes: List[List[float]],
) -> Optional[List[float]]:
    valid = [
        bbox
        for bbox in bboxes
        if bbox and len(bbox) >= 4
    ]

    if not valid:
        return None

    x0 = min(
        safe_float(b[0])
        for b in valid
    )

    y0 = min(
        safe_float(b[1])
        for b in valid
    )

    x1 = max(
        safe_float(b[2])
        for b in valid
    )

    y1 = max(
        safe_float(b[3])
        for b in valid
    )

    return [
        round(x0, 3),
        round(y0, 3),
        round(x1, 3),
        round(y1, 3),
    ]


def horizontal_gap(
    bbox_a: List[float],
    bbox_b: List[float],
) -> float:
    ax0, _, ax1, _ = bbox_a
    bx0, _, bx1, _ = bbox_b

    if ax1 < bx0:
        return bx0 - ax1

    if bx1 < ax0:
        return ax0 - bx1

    return 0.0


def vertical_gap(
    bbox_a: List[float],
    bbox_b: List[float],
) -> float:
    _, ay0, _, ay1 = bbox_a
    _, by0, _, by1 = bbox_b

    if ay1 < by0:
        return by0 - ay1

    if by1 < ay0:
        return ay0 - by1

    return 0.0


def horizontal_region(
    bbox: List[float],
    page_width: float,
) -> str:
    if not bbox or page_width <= 0:
        return "unknown"

    center_x = bbox_center(bbox)[0]

    ratio = center_x / page_width

    if ratio < 0.33:
        return "left"

    if ratio < 0.67:
        return "center"

    return "right"


def detect_page_geometry(
    page: dict,
    elements: list[dict],
) -> dict:
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
                and len(
                    element.get("bbox")
                ) >= 4
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
                and len(
                    element.get("bbox")
                ) >= 4
            ),
            default=0.0,
        )

    return {
        "width": round(
            page_width,
            3,
        ),
        "height": round(
            page_height,
            3,
        ),
    }
