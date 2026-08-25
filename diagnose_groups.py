"""
VKS Expert AI — Formula Group Diagnostics v0.8.8

Диагностика составных групп формул.

v0.8.8
------
Изменения относительно v0.8.7:

    • fitz заменён на современный import pymupdf;
    • добавлен явный --pdf-file;
    • добавлен автоматический поиск исходного PDF;
    • composite crop строится непосредственно из страницы PDF;
    • element crops продолжают строиться из исходных image-файлов;
    • PDF source выводится в диагностике;
    • если PDF не найден, element crops не теряются;
    • crop padding для composite crop задаётся в PDF points;
    • добавлена защита crop от выхода за границы страницы;
    • количество element/composite crops выводится отдельно;
    • сохранена вся геометрическая диагностика v0.8.7;
    • сохранена GROUP DECISION;
    • сохранён JSON DIAGNOSTICS;
    • Pillow остаётся опциональной зависимостью;
    • PyMuPDF необходим только для composite crop.

Примеры:

    python diagnose_groups.py --page 12 --group 13

    python diagnose_groups.py --page 12 --group 13 --geometry

    python diagnose_groups.py --page 12 --group 13 --geometry --crop

    python diagnose_groups.py --page 12 --group 13 --geometry --crop ^
        --pdf-file "knowledge\\source\\SP_30.13330.2020.pdf"

    python diagnose_groups.py --page 12 --group 13 --geometry --crop ^
        --crop-padding 10

    python diagnose_groups.py --page 12 --geometry --crop --limit 5

    python diagnose_groups.py --all --geometry --crop --limit 20
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


VERSION = "0.8.8"

DEFAULT_SEMANTIC_FILE = (
    Path("knowledge")
    / "parsed"
    / "SP_30.13330.2020.semantic.json"
)


# ============================================================================
# BASIC HELPERS
# ============================================================================


def fmt_number(value: Any, digits: int = 2) -> str:
    """Безопасное форматирование числового значения."""

    if value is None:
        return "None"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_bbox(
    bbox: Optional[Sequence[Any]],
) -> str:
    """Форматирует bbox."""

    if not bbox or len(bbox) != 4:
        return "None"

    return (
        "["
        f"{fmt_number(bbox[0])}, "
        f"{fmt_number(bbox[1])}, "
        f"{fmt_number(bbox[2])}, "
        f"{fmt_number(bbox[3])}"
        "]"
    )


def bbox_width(
    bbox: Sequence[Any],
) -> float:
    return float(bbox[2]) - float(bbox[0])


def bbox_height(
    bbox: Sequence[Any],
) -> float:
    return float(bbox[3]) - float(bbox[1])


def bbox_area(
    bbox: Sequence[Any],
) -> float:
    return (
        max(0.0, bbox_width(bbox))
        * max(0.0, bbox_height(bbox))
    )


def bbox_center(
    bbox: Sequence[Any],
) -> Tuple[float, float]:
    return (
        (float(bbox[0]) + float(bbox[2])) / 2.0,
        (float(bbox[1]) + float(bbox[3])) / 2.0,
    )


def safe_int(
    value: Any,
) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(
    value: Any,
) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ============================================================================
# GEOMETRY
# ============================================================================


def horizontal_overlap(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    return max(
        0.0,
        min(
            float(a[2]),
            float(b[2]),
        )
        - max(
            float(a[0]),
            float(b[0]),
        ),
    )


def vertical_overlap(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    return max(
        0.0,
        min(
            float(a[3]),
            float(b[3]),
        )
        - max(
            float(a[1]),
            float(b[1]),
        ),
    )


def horizontal_gap(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    if float(a[2]) < float(b[0]):
        return float(b[0]) - float(a[2])

    if float(b[2]) < float(a[0]):
        return float(a[0]) - float(b[2])

    return 0.0


def vertical_gap(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    if float(a[3]) < float(b[1]):
        return float(b[1]) - float(a[3])

    if float(b[3]) < float(a[1]):
        return float(a[1]) - float(b[3])

    return 0.0


def intersection_area(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    width = horizontal_overlap(a, b)
    height = vertical_overlap(a, b)

    return width * height


def union_area(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    return (
        bbox_area(a)
        + bbox_area(b)
        - intersection_area(a, b)
    )


def iou(
    a: Sequence[Any],
    b: Sequence[Any],
) -> float:

    union = union_area(a, b)

    if union <= 0:
        return 0.0

    return intersection_area(a, b) / union


def same_row(
    a: Sequence[Any],
    b: Sequence[Any],
    tolerance: float = 3.0,
) -> bool:

    cy_a = bbox_center(a)[1]
    cy_b = bbox_center(b)[1]

    return abs(cy_a - cy_b) <= tolerance


def same_column(
    a: Sequence[Any],
    b: Sequence[Any],
    tolerance: float = 3.0,
) -> bool:

    cx_a = bbox_center(a)[0]
    cx_b = bbox_center(b)[0]

    return abs(cx_a - cx_b) <= tolerance


def relative_position(
    a: Sequence[Any],
    b: Sequence[Any],
) -> str:

    ax, ay = bbox_center(a)
    bx, by = bbox_center(b)

    dx = bx - ax
    dy = by - ay

    if abs(dx) >= abs(dy):

        if dx >= 0:
            return "left"

        return "right"

    if dy >= 0:
        return "above"

    return "below"


def calculate_group_bbox(
    members: Sequence[Dict[str, Any]],
) -> Optional[List[float]]:
    """Рассчитывает bbox группы по bbox её элементов."""

    boxes = [
        member.get("bbox")
        for member in members
        if member.get("bbox")
        and len(member.get("bbox")) == 4
    ]

    if not boxes:
        return None

    x0 = min(
        float(box[0])
        for box in boxes
    )

    y0 = min(
        float(box[1])
        for box in boxes
    )

    x1 = max(
        float(box[2])
        for box in boxes
    )

    y1 = max(
        float(box[3])
        for box in boxes
    )

    return [
        x0,
        y0,
        x1,
        y1,
    ]


# ============================================================================
# CLASSIFICATION
# ============================================================================


def get_classification(
    element: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Безопасно извлекает classification.

    Поддерживаются:

        "classification": {
            "reason": "...",
            "confidence": 0.75
        }

    и плоские поля.
    """

    classification = element.get(
        "classification"
    )

    if isinstance(
        classification,
        dict,
    ):
        return classification

    reason = element.get(
        "classification_reason"
    )

    confidence = element.get(
        "classification_confidence"
    )

    if (
        reason is not None
        or confidence is not None
    ):
        return {
            "reason": reason,
            "confidence": confidence,
        }

    return {}


def classification_reason(
    element: Dict[str, Any],
) -> Any:

    classification = get_classification(
        element
    )

    return classification.get(
        "reason"
    )


def classification_confidence(
    element: Dict[str, Any],
) -> Any:

    classification = get_classification(
        element
    )

    return classification.get(
        "confidence"
    )


# ============================================================================
# DATA LOADING
# ============================================================================


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        print()
        print(
            "ОШИБКА: semantic JSON не найден:"
        )
        print(path)
        print()

        sys.exit(1)

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except json.JSONDecodeError as exc:

        print()
        print(
            "ОШИБКА: некорректный JSON:"
        )
        print(path)
        print(exc)
        print()

        sys.exit(1)


def page_number(
    page: Dict[str, Any],
    fallback: int,
) -> int:

    value = page.get(
        "page_number"
    )

    if value is None:
        value = page.get(
            "page"
        )

    if value is None:
        return fallback

    parsed = safe_int(
        value
    )

    return (
        parsed
        if parsed is not None
        else fallback
    )


def get_pages(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    pages = data.get(
        "pages",
        [],
    )

    if not isinstance(
        pages,
        list,
    ):
        return []

    return pages


# ============================================================================
# GROUP MEMBERS
# ============================================================================


def resolve_group_members(
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Восстанавливает реальные элементы группы.

    Основной источник — parser_indices.
    """

    elements = page.get(
        "elements",
        [],
    )

    if not isinstance(
        elements,
        list,
    ):
        elements = []

    by_parser_index: Dict[
        int,
        Dict[str, Any],
    ] = {}

    for element in elements:

        index = safe_int(
            element.get(
                "parser_index"
            )
        )

        if index is not None:

            by_parser_index[
                index
            ] = element

    parser_indices = group.get(
        "parser_indices",
        [],
    )

    result = []

    if isinstance(
        parser_indices,
        list,
    ):

        for index in parser_indices:

            parsed_index = safe_int(
                index
            )

            if parsed_index is None:
                continue

            element = by_parser_index.get(
                parsed_index
            )

            if element is not None:

                result.append(
                    element
                )

    return result


def get_group_id(
    group: Dict[str, Any],
) -> Optional[int]:

    return safe_int(
        group.get("group_id")
    )


def group_is_composite(
    group: Dict[str, Any],
) -> bool:

    return bool(
        group.get("composite")
    )


def group_has_relation(
    page: Dict[str, Any],
    group_id: Optional[int],
) -> bool:

    if group_id is None:
        return False

    relations = page.get(
        "formula_relations",
        [],
    )

    if not isinstance(
        relations,
        list,
    ):
        return False

    for relation in relations:

        relation_group_id = safe_int(
            relation.get(
                "group_id"
            )
        )

        if relation_group_id == group_id:
            return True

    return False


# ============================================================================
# GROUP SELECTION
# ============================================================================


def get_unnumbered_composite_groups(
    data: Dict[str, Any],
) -> List[
    Tuple[
        int,
        Dict[str, Any],
        Dict[str, Any],
    ]
]:

    result = []

    pages = get_pages(
        data
    )

    for (
        fallback_page_number,
        page,
    ) in enumerate(
        pages,
        start=1,
    ):

        current_page_number = page_number(
            page,
            fallback_page_number,
        )

        groups = page.get(
            "formula_groups",
            [],
        )

        if not isinstance(
            groups,
            list,
        ):
            continue

        relations = page.get(
            "formula_relations",
            [],
        )

        relation_ids = set()

        if isinstance(
            relations,
            list,
        ):

            for relation in relations:

                group_id = safe_int(
                    relation.get(
                        "group_id"
                    )
                )

                if group_id is not None:

                    relation_ids.add(
                        group_id
                    )

        for group in groups:

            if not isinstance(
                group,
                dict,
            ):
                continue

            if not group_is_composite(
                group
            ):
                continue

            group_id = get_group_id(
                group
            )

            if group_id in relation_ids:
                continue

            result.append(
                (
                    current_page_number,
                    page,
                    group,
                )
            )

    return result


# ============================================================================
# IMAGE RESOLUTION
# ============================================================================


def image_directory_from_semantic_file(
    semantic_file: Path,
) -> Path:
    """
    SP_30.13330.2020.semantic.json
        ->
    SP_30.13330.2020.images
    """

    name = semantic_file.name

    suffix = ".semantic.json"

    if name.endswith(
        suffix
    ):

        base_name = name[
            : -len(suffix)
        ]

    else:

        base_name = semantic_file.stem

    return (
        semantic_file.parent
        / f"{base_name}.images"
    )


def find_image_file(
    semantic_file: Path,
    element: Dict[str, Any],
) -> Optional[Path]:
    """
    Ищет PNG/JPG изображения элемента.

    Приоритет:

        1. file
        2. xref -> image_xref_<xref>.png
    """

    file_value = element.get(
        "file"
    )

    if file_value:

        candidate = Path(
            str(file_value)
        )

        if candidate.exists():
            return candidate

        candidate_relative = (
            semantic_file.parent.parent
            / candidate
        )

        if candidate_relative.exists():
            return candidate_relative

        candidate_project = (
            Path.cwd()
            / candidate
        )

        if candidate_project.exists():
            return candidate_project

    xref = element.get(
        "xref"
    )

    if xref is None:
        return None

    image_dir = image_directory_from_semantic_file(
        semantic_file
    )

    candidates = [
        image_dir
        / f"image_xref_{xref}.png",

        image_dir
        / f"image_xref_{xref}.jpg",

        image_dir
        / f"image_xref_{xref}.jpeg",

        image_dir
        / f"image_xref_{xref}.webp",
    ]

    for candidate in candidates:

        if candidate.exists():
            return candidate

    return None


def get_image_size(
    path: Optional[Path],
) -> Optional[
    Tuple[int, int]
]:

    if path is None:
        return None

    try:

        from PIL import Image

    except ImportError:

        return None

    try:

        with Image.open(
            path
        ) as image:

            return image.size

    except Exception:

        return None


# ============================================================================
# PDF RESOLUTION
# ============================================================================


def semantic_pdf_basename(
    semantic_file: Path,
) -> str:
    """
    Извлекает basename исходного PDF.

    Например:

        SP_30.13330.2020.semantic.json
        ->
        SP_30.13330.2020
    """

    suffix = ".semantic.json"

    if semantic_file.name.endswith(
        suffix
    ):

        return semantic_file.name[
            : -len(suffix)
        ]

    return semantic_file.stem


def unique_paths(
    paths: Sequence[Path],
) -> List[Path]:

    result = []

    seen = set()

    for path in paths:

        try:

            key = str(
                path.resolve()
            ).lower()

        except Exception:

            key = str(
                path
            ).lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(path)

    return result


def resolve_pdf_file(
    semantic_file: Path,
    explicit_pdf: Optional[Path],
) -> Tuple[
    Optional[Path],
    str,
]:
    """
    Определяет исходный PDF.

    Приоритет:

        1. --pdf-file
        2. PDF рядом с semantic JSON
        3. knowledge/parsed/
        4. knowledge/
        5. knowledge/source/
        6. knowledge/regulations/
        7. project root

    Возвращает:

        (resolved_path, status)
    """

    basename = semantic_pdf_basename(
        semantic_file
    )

    if explicit_pdf is not None:

        candidates = []

        if explicit_pdf.is_absolute():

            candidates.append(
                explicit_pdf
            )

        else:

            candidates.append(
                Path.cwd()
                / explicit_pdf
            )

            candidates.append(
                explicit_pdf
            )

        candidates = unique_paths(
            candidates
        )

        for candidate in candidates:

            if candidate.exists() and candidate.is_file():

                return (
                    candidate.resolve(),
                    "EXPLICIT",
                )

        return (
            None,
            "EXPLICIT_NOT_FOUND",
        )

    project_root = Path.cwd()

    candidates = [
        semantic_file.parent
        / f"{basename}.pdf",

        project_root
        / f"{basename}.pdf",

        semantic_file.parent.parent
        / f"{basename}.pdf",

        semantic_file.parent.parent
        / "source"
        / f"{basename}.pdf",

        semantic_file.parent.parent
        / "regulations"
        / f"{basename}.pdf",

        project_root
        / "knowledge"
        / f"{basename}.pdf",

        project_root
        / "knowledge"
        / "source"
        / f"{basename}.pdf",

        project_root
        / "knowledge"
        / "regulations"
        / f"{basename}.pdf",
    ]

    candidates = unique_paths(
        candidates
    )

    for candidate in candidates:

        if candidate.exists() and candidate.is_file():

            return (
                candidate.resolve(),
                "AUTO",
            )

    return (
        None,
        "NOT_FOUND",
    )


def print_pdf_source(
    semantic_file: Path,
    pdf_file: Optional[Path],
    pdf_status: str,
) -> None:

    print()
    print(
        "PDF SOURCE"
    )
    print(
        "-" * 80
    )

    print(
        f"    semantic basename : "
        f"{semantic_pdf_basename(semantic_file)}"
    )

    if pdf_file:

        print(
            f"    resolved PDF      : "
            f"{pdf_file}"
        )

    else:

        print(
            "    resolved PDF      : NOT FOUND"
        )

    print(
        f"    status            : "
        f"{pdf_status}"
    )

    if pdf_status == "NOT_FOUND":

        print()
        print(
            "    Composite crop будет пропущен."
        )

        print(
            "    Element crops продолжат создаваться."
        )

    elif pdf_status == "EXPLICIT_NOT_FOUND":

        print()
        print(
            "    Указанный --pdf-file не найден."
        )

        print(
            "    Проверьте путь к исходному PDF."
        )


# ============================================================================
# OUTPUT
# ============================================================================


def print_header(
    semantic_file: Path,
    pages: Sequence[Dict[str, Any]],
    unnumbered_count: int,
) -> None:

    print(
        f"VKS Expert AI — "
        f"Formula Group Diagnostics "
        f"v{VERSION}"
    )

    print(
        "=" * 80
    )

    print(
        f"Semantic file: "
        f"{semantic_file}"
    )

    print(
        f"Pages: "
        f"{len(pages)}"
    )

    print(
        f"Unnumbered composite groups: "
        f"{unnumbered_count}"
    )


def print_formula_relations(
    page: Dict[str, Any],
    group_id: Optional[int],
) -> None:

    print()
    print(
        "FORMULA RELATIONS:"
    )

    print(
        "-" * 80
    )

    relations = page.get(
        "formula_relations",
        [],
    )

    matches = []

    if isinstance(
        relations,
        list,
    ):

        for relation in relations:

            relation_group_id = safe_int(
                relation.get(
                    "group_id"
                )
            )

            if relation_group_id == group_id:

                matches.append(
                    relation
                )

    if not matches:

        print(
            "    none"
        )

        return

    for relation in matches:

        print(
            "    "
            f"group_id={relation.get('group_id')} "
            f"number={relation.get('number')} "
            f"score={relation.get('score')}"
        )


def print_group_geometry(
    members: Sequence[Dict[str, Any]],
    declared_bbox: Optional[Sequence[Any]],
) -> None:

    print()
    print(
        "GROUP GEOMETRY"
    )

    print(
        "-" * 80
    )

    calculated_bbox = calculate_group_bbox(
        members
    )

    print(
        "    calculated bbox : "
        f"{fmt_bbox(calculated_bbox)}"
    )

    if calculated_bbox:

        width = bbox_width(
            calculated_bbox
        )

        height = bbox_height(
            calculated_bbox
        )

        area = bbox_area(
            calculated_bbox
        )

        cx, cy = bbox_center(
            calculated_bbox
        )

        print(
            f"    width           : "
            f"{width:.2f}"
        )

        print(
            f"    height          : "
            f"{height:.2f}"
        )

        print(
            f"    area            : "
            f"{area:.2f}"
        )

        print(
            f"    center          : "
            f"({cx:.2f}, {cy:.2f})"
        )

    if declared_bbox:

        print()

        print(
            "    declared bbox   : "
            f"{fmt_bbox(declared_bbox)}"
        )

        if calculated_bbox:

            dx0 = (
                float(declared_bbox[0])
                - calculated_bbox[0]
            )

            dy0 = (
                float(declared_bbox[1])
                - calculated_bbox[1]
            )

            dx1 = (
                float(declared_bbox[2])
                - calculated_bbox[2]
            )

            dy1 = (
                float(declared_bbox[3])
                - calculated_bbox[3]
            )

            print(
                "    bbox delta      : "
                f"[{dx0:.2f}, {dy0:.2f}, "
                f"{dx1:.2f}, {dy1:.2f}]"
            )


def print_element(
    semantic_file: Path,
    element: Dict[str, Any],
    number: int,
) -> None:

    bbox = element.get(
        "bbox"
    )

    print()
    print(
        f"    ELEMENT #{number}"
    )

    print(
        "    " + "-" * 68
    )

    print(
        f"    parser_index : "
        f"{element.get('parser_index')}"
    )

    print(
        f"    source_index : "
        f"{element.get('source_index')}"
    )

    print(
        f"    xref         : "
        f"{element.get('xref')}"
    )

    print(
        f"    type         : "
        f"{element.get('type')}"
    )

    print(
        f"    element_type : "
        f"{element.get('element_type')}"
    )

    print(
        f"    semantic_role: "
        f"{element.get('semantic_role')}"
    )

    print(
        f"    bbox         : "
        f"{fmt_bbox(bbox)}"
    )

    if bbox and len(bbox) == 4:

        print(
            f"    width        : "
            f"{bbox_width(bbox):.2f}"
        )

        print(
            f"    height       : "
            f"{bbox_height(bbox):.2f}"
        )

        print(
            f"    area         : "
            f"{bbox_area(bbox):.2f}"
        )

        cx, cy = bbox_center(
            bbox
        )

        print(
            f"    center       : "
            f"({cx:.2f}, {cy:.2f})"
        )

    image_file = find_image_file(
        semantic_file,
        element,
    )

    print(
        f"    file         : "
        f"{element.get('file')}"
    )

    if image_file:

        print(
            f"    resolved file : "
            f"{image_file}"
        )

        image_size = get_image_size(
            image_file
        )

        if image_size:

            print(
                f"    image size    : "
                f"{image_size[0]} x "
                f"{image_size[1]} px"
            )

    else:

        print(
            "    resolved file : NOT FOUND"
        )

    classification = get_classification(
        element
    )

    print(
        "    classification:"
    )

    print(
        f"        reason     = "
        f"{classification.get('reason')}"
    )

    print(
        f"        confidence = "
        f"{classification.get('confidence')}"
    )


def print_distributions(
    members: Sequence[Dict[str, Any]],
) -> None:

    print()
    print(
        "ROLE DISTRIBUTION"
    )

    print(
        "-" * 80
    )

    roles = Counter(
        element.get(
            "semantic_role"
        )
        for element in members
    )

    if not roles:

        print(
            "    none"
        )

    else:

        for role, count in roles.most_common():

            print(
                f"    {role}: {count}"
            )

    print()
    print(
        "CLASSIFICATION DISTRIBUTION"
    )

    print(
        "-" * 80
    )

    reasons = Counter(
        classification_reason(
            element
        )
        for element in members
    )

    for reason, count in reasons.most_common():

        print(
            f"    {reason}: {count}"
        )

    print()
    print(
        "CONFIDENCE DISTRIBUTION"
    )

    print(
        "-" * 80
    )

    confidences = Counter()

    for element in members:

        confidence = classification_confidence(
            element
        )

        if isinstance(
            confidence,
            float,
        ):

            key = f"{confidence:.2f}"

        elif isinstance(
            confidence,
            int,
        ):

            key = f"{confidence:.2f}"

        else:

            key = str(
                confidence
            )

        confidences[key] += 1

    for confidence, count in (
        confidences.most_common()
    ):

        print(
            f"    {confidence}: {count}"
        )


def print_pairwise_geometry(
    members: Sequence[Dict[str, Any]],
) -> None:

    print()
    print(
        "PAIRWISE GEOMETRY"
    )

    print(
        "-" * 80
    )

    if len(members) < 2:

        print(
            "    not enough members"
        )

        return

    for first, second in zip(
        members,
        members[1:],
    ):

        bbox_a = first.get(
            "bbox"
        )

        bbox_b = second.get(
            "bbox"
        )

        if not bbox_a or not bbox_b:
            continue

        first_index = first.get(
            "parser_index"
        )

        second_index = second.get(
            "parser_index"
        )

        print(
            f"    {first_index} -> "
            f"{second_index}"
        )

        print(
            f"        horizontal_gap      : "
            f"{horizontal_gap(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        vertical_gap        : "
            f"{vertical_gap(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        horizontal_overlap  : "
            f"{horizontal_overlap(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        vertical_overlap    : "
            f"{vertical_overlap(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        intersection_area   : "
            f"{intersection_area(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        union_area          : "
            f"{union_area(bbox_a, bbox_b):.2f}"
        )

        print(
            f"        IoU                  : "
            f"{iou(bbox_a, bbox_b):.4f}"
        )

        print(
            f"        same_row             : "
            f"{same_row(bbox_a, bbox_b)}"
        )

        print(
            f"        same_column          : "
            f"{same_column(bbox_a, bbox_b)}"
        )

        print(
            f"        relative_position    : "
            f"{relative_position(bbox_a, bbox_b)}"
        )


# ============================================================================
# GROUP DECISION
# ============================================================================


def calculate_uniformity(
    values: Sequence[float],
) -> float:
    """
    Возвращает коэффициент однородности.

    1.0 = полностью одинаковые значения.
    Чем меньше значение, тем сильнее разброс.
    """

    if not values:
        return 0.0

    if len(values) == 1:
        return 1.0

    maximum = max(values)

    if maximum <= 0:
        return 1.0

    minimum = min(values)

    return max(
        0.0,
        min(
            1.0,
            minimum / maximum,
        ),
    )


def calculate_gap_score(
    horizontal_gaps: Sequence[float],
) -> float:
    """
    Эвристическая оценка горизонтальных промежутков.

    <= 10 pt  -> 1.0
    >= 40 pt  -> 0.3

    Между ними линейная интерполяция.
    """

    if not horizontal_gaps:
        return 1.0

    mean_gap = sum(
        horizontal_gaps
    ) / len(horizontal_gaps)

    if mean_gap <= 10.0:
        return 1.0

    if mean_gap >= 40.0:
        return 0.3

    return (
        1.0
        - (
            (mean_gap - 10.0)
            / 30.0
        )
        * 0.7
    )


def calculate_vertical_score(
    vertical_gaps: Sequence[float],
) -> float:

    if not vertical_gaps:
        return 1.0

    maximum = max(
        vertical_gaps
    )

    if maximum <= 3.0:
        return 1.0

    if maximum >= 20.0:
        return 0.0

    return max(
        0.0,
        min(
            1.0,
            1.0
            - (
                (maximum - 3.0)
                / 17.0
            ),
        ),
    )


def calculate_row_score(
    members: Sequence[Dict[str, Any]],
) -> float:

    if len(members) < 2:
        return 1.0

    comparisons = 0
    matches = 0

    for first, second in zip(
        members,
        members[1:],
    ):

        bbox_a = first.get(
            "bbox"
        )

        bbox_b = second.get(
            "bbox"
        )

        if not bbox_a or not bbox_b:
            continue

        comparisons += 1

        if same_row(
            bbox_a,
            bbox_b,
        ):
            matches += 1

    if comparisons == 0:
        return 0.0

    return (
        matches
        / comparisons
    )


def calculate_role_score(
    members: Sequence[Dict[str, Any]],
) -> float:

    roles = [
        element.get(
            "semantic_role"
        )
        for element in members
    ]

    roles = [
        role
        for role in roles
        if role
    ]

    if not roles:
        return 0.0

    formula_roles = {
        "formula",
        "formula_fragment",
        "formula_candidate",
    }

    compatible = sum(
        1
        for role in roles
        if role in formula_roles
    )

    return (
        compatible
        / len(roles)
    )


def calculate_classification_score(
    members: Sequence[Dict[str, Any]],
) -> float:

    reasons = [
        classification_reason(
            element
        )
        for element in members
    ]

    reasons = [
        reason
        for reason in reasons
        if reason
    ]

    if not reasons:
        return 0.0

    unique = set(
        reasons
    )

    if len(unique) == 1:
        return 1.0

    if len(unique) == len(reasons):
        return 0.5

    return 0.75


def calculate_confidence_score(
    members: Sequence[Dict[str, Any]],
) -> float:

    values = []

    for element in members:

        confidence = safe_float(
            classification_confidence(
                element
            )
        )

        if confidence is not None:

            values.append(
                confidence
            )

    if not values:
        return 0.0

    return sum(
        values
    ) / len(values)


def calculate_group_decision(
    members: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:

    horizontal_gaps = []
    vertical_gaps = []

    for first, second in zip(
        members,
        members[1:],
    ):

        bbox_a = first.get(
            "bbox"
        )

        bbox_b = second.get(
            "bbox"
        )

        if not bbox_a or not bbox_b:
            continue

        horizontal_gaps.append(
            horizontal_gap(
                bbox_a,
                bbox_b,
            )
        )

        vertical_gaps.append(
            vertical_gap(
                bbox_a,
                bbox_b,
            )
        )

    widths = []
    heights = []

    element_area = 0.0

    for member in members:

        bbox = member.get(
            "bbox"
        )

        if not bbox or len(bbox) != 4:
            continue

        width = bbox_width(
            bbox
        )

        height = bbox_height(
            bbox
        )

        widths.append(
            max(
                0.0,
                width,
            )
        )

        heights.append(
            max(
                0.0,
                height,
            )
        )

        element_area += bbox_area(
            bbox
        )

    group_bbox = calculate_group_bbox(
        members
    )

    if group_bbox:

        group_area = bbox_area(
            group_bbox
        )

    else:

        group_area = 0.0

    if group_area > 0:

        bbox_fill_ratio = min(
            1.0,
            element_area
            / group_area,
        )

    else:

        bbox_fill_ratio = 0.0

    min_horizontal_gap = (
        min(horizontal_gaps)
        if horizontal_gaps
        else 0.0
    )

    mean_horizontal_gap = (
        sum(horizontal_gaps)
        / len(horizontal_gaps)
        if horizontal_gaps
        else 0.0
    )

    max_horizontal_gap = (
        max(horizontal_gaps)
        if horizontal_gaps
        else 0.0
    )

    max_vertical_gap = (
        max(vertical_gaps)
        if vertical_gaps
        else 0.0
    )

    same_row_ratio = calculate_row_score(
        members
    )

    height_uniformity = calculate_uniformity(
        heights
    )

    width_uniformity = calculate_uniformity(
        widths
    )

    gap_score = calculate_gap_score(
        horizontal_gaps
    )

    vertical_score = calculate_vertical_score(
        vertical_gaps
    )

    row_score = same_row_ratio

    height_score = height_uniformity

    width_score = width_uniformity

    fill_score = bbox_fill_ratio

    role_score = calculate_role_score(
        members
    )

    classification_score = (
        calculate_classification_score(
            members
        )
    )

    confidence_score = (
        calculate_confidence_score(
            members
        )
    )

    quality_score = (
        gap_score * 0.20
        + vertical_score * 0.10
        + row_score * 0.10
        + height_score * 0.10
        + width_score * 0.05
        + fill_score * 0.10
        + role_score * 0.10
        + classification_score * 0.10
        + confidence_score * 0.15
    )

    if quality_score >= 0.85:

        quality = "HIGH"

    elif quality_score >= 0.65:

        quality = "MEDIUM"

    else:

        quality = "LOW"

    reasons = []

    if mean_horizontal_gap <= 10:

        reasons.append(
            "small horizontal gaps"
        )

    elif mean_horizontal_gap >= 30:

        reasons.append(
            "large horizontal gap"
        )

    else:

        reasons.append(
            "moderate horizontal gaps"
        )

    if same_row_ratio >= 0.8:

        reasons.append(
            "members are aligned on the same row"
        )

    elif same_row_ratio <= 0.3:

        reasons.append(
            "members are not aligned on the same row"
        )

    if height_uniformity >= 0.85:

        reasons.append(
            "member heights are highly uniform"
        )

    if width_uniformity >= 0.85:

        reasons.append(
            "member widths are highly uniform"
        )

    if bbox_fill_ratio >= 0.70:

        reasons.append(
            "group bbox has high element occupancy"
        )

    if role_score >= 0.75:

        reasons.append(
            "semantic roles are compatible"
        )

    if classification_score >= 0.90:

        reasons.append(
            "classifications are consistent"
        )

    elif classification_score < 0.60:

        reasons.append(
            "classifications are heterogeneous"
        )

    return {
        "member_count": len(members),

        "horizontal_gaps": horizontal_gaps,
        "vertical_gaps": vertical_gaps,

        "min_horizontal_gap": min_horizontal_gap,
        "mean_horizontal_gap": mean_horizontal_gap,
        "max_horizontal_gap": max_horizontal_gap,

        "max_vertical_gap": max_vertical_gap,

        "same_row_ratio": same_row_ratio,

        "height_uniformity": height_uniformity,
        "width_uniformity": width_uniformity,

        "bbox_fill_ratio": bbox_fill_ratio,

        "gap_score": gap_score,
        "vertical_score": vertical_score,
        "row_score": row_score,
        "height_score": height_score,
        "width_score": width_score,
        "fill_score": fill_score,
        "role_score": role_score,
        "classification_score": classification_score,
        "confidence_score": confidence_score,

        "quality_score": quality_score,
        "quality": quality,

        "reasons": reasons,
    }


def print_group_decision(
    members: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:

    decision = calculate_group_decision(
        members
    )

    print()
    print(
        "GROUP DECISION"
    )

    print(
        "-" * 80
    )

    print(
        f"    member_count          : "
        f"{decision['member_count']}"
    )

    print()

    print(
        f"    min_horizontal_gap    : "
        f"{decision['min_horizontal_gap']:.2f} pt"
    )

    print(
        f"    mean_horizontal_gap   : "
        f"{decision['mean_horizontal_gap']:.2f} pt"
    )

    print(
        f"    max_horizontal_gap    : "
        f"{decision['max_horizontal_gap']:.2f} pt"
    )

    print(
        f"    max_vertical_gap      : "
        f"{decision['max_vertical_gap']:.2f} pt"
    )

    print()

    print(
        f"    same_row_ratio        : "
        f"{decision['same_row_ratio']:.3f}"
    )

    print(
        f"    height_uniformity     : "
        f"{decision['height_uniformity']:.3f}"
    )

    print(
        f"    width_uniformity      : "
        f"{decision['width_uniformity']:.3f}"
    )

    print(
        f"    bbox_fill_ratio       : "
        f"{decision['bbox_fill_ratio']:.3f}"
    )

    print()

    print(
        "    COMPONENT SCORES"
    )

    print(
        f"        gap_score             : "
        f"{decision['gap_score']:.3f}"
    )

    print(
        f"        vertical_score        : "
        f"{decision['vertical_score']:.3f}"
    )

    print(
        f"        row_score             : "
        f"{decision['row_score']:.3f}"
    )

    print(
        f"        height_score          : "
        f"{decision['height_score']:.3f}"
    )

    print(
        f"        width_score           : "
        f"{decision['width_score']:.3f}"
    )

    print(
        f"        fill_score            : "
        f"{decision['fill_score']:.3f}"
    )

    print(
        f"        role_score            : "
        f"{decision['role_score']:.3f}"
    )

    print(
        f"        classification_score  : "
        f"{decision['classification_score']:.3f}"
    )

    print(
        f"        confidence_score      : "
        f"{decision['confidence_score']:.3f}"
    )

    print()

    print(
        f"    QUALITY SCORE          : "
        f"{decision['quality_score']:.3f}"
    )

    print(
        f"    GROUP QUALITY          : "
        f"{decision['quality']}"
    )

    print()

    print(
        "    REASONS:"
    )

    for reason in decision["reasons"]:

        print(
            f"        - {reason}"
        )

    print()

    print(
        "    NOTE:"
    )

    print(
        "        This is a diagnostic heuristic only."
    )

    print(
        "        It does not modify formula_groups."
    )

    return decision


# ============================================================================
# CROPS
# ============================================================================


def require_pillow() -> Any:

    try:

        from PIL import Image

    except ImportError:

        print()
        print(
            "WARNING: Pillow не установлен."
        )

        print(
            "Установите:"
        )

        print(
            "    pip install pillow"
        )

        print()

        return None

    return Image


def require_pymupdf() -> Any:

    try:

        import pymupdf

        return pymupdf

    except ImportError:

        print()
        print(
            "WARNING: PyMuPDF не установлен."
        )

        print(
            "Он необходим для composite crop."
        )

        print(
            "Установите:"
        )

        print(
            "    pip install pymupdf"
        )

        print()

        return None


def crop_group_images(
    semantic_file: Path,
    page: Dict[str, Any],
    group: Dict[str, Any],
    output_dir: Path,
    padding: float,
    open_crops: bool = False,
) -> List[Path]:
    """
    Создаёт crops исходных image-файлов элементов группы.

    Важно:

    bbox в semantic JSON находится
    в координатах PDF.

    PNG image_xref_* являются
    отдельными raster-изображениями.

    Поэтому element crop не пытается
    интерпретировать PDF bbox как координаты PNG.
    """

    Image = require_pillow()

    if Image is None:
        return []

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_no = page_number(
        page,
        0,
    )

    group_id = get_group_id(
        group
    )

    members = resolve_group_members(
        page,
        group,
    )

    generated = []

    for position, element in enumerate(
        members,
        start=1,
    ):

        image_file = find_image_file(
            semantic_file,
            element,
        )

        if image_file is None:

            print(
                f"    element crop #{position}: "
                f"image not found"
            )

            continue

        try:

            with Image.open(
                image_file
            ) as image:

                width, height = image.size

                pad = max(
                    0,
                    int(
                        round(
                            padding
                        )
                    ),
                )

                crop_box = (
                    0,
                    0,
                    width,
                    height,
                )

                cropped = image.crop(
                    crop_box
                )

                xref = element.get(
                    "xref",
                    f"element_{position}",
                )

                filename = (
                    f"page_{page_no:03d}"
                    f"_group_{group_id}"
                    f"_element_{position}"
                    f"_xref_{xref}.png"
                )

                output_path = (
                    output_dir
                    / filename
                )

                cropped.save(
                    output_path
                )

                generated.append(
                    output_path
                )

                print(
                    f"    element crop #{position}: "
                    f"{output_path}"
                )

        except Exception as exc:

            print(
                f"    element crop #{position}: "
                f"ERROR: {exc}"
            )

    return generated


def calculate_pdf_crop_rect(
    page_rect: Any,
    bbox: Sequence[Any],
    padding: float,
) -> Any:
    """
    Рассчитывает прямоугольник crop
    в координатах PDF.

    Координаты semantic JSON
    и PyMuPDF предполагаются
    согласованными по системе координат
    страницы.
    """

    x0 = float(bbox[0]) - padding
    y0 = float(bbox[1]) - padding
    x1 = float(bbox[2]) + padding
    y1 = float(bbox[3]) + padding

    x0 = max(
        float(page_rect.x0),
        x0,
    )

    y0 = max(
        float(page_rect.y0),
        y0,
    )

    x1 = min(
        float(page_rect.x1),
        x1,
    )

    y1 = min(
        float(page_rect.y1),
        y1,
    )

    if x1 <= x0:
        x1 = x0 + 1.0

    if y1 <= y0:
        y1 = y0 + 1.0

    return (
        x0,
        y0,
        x1,
        y1,
    )


def crop_group_from_pdf(
    pdf_file: Optional[Path],
    page: Dict[str, Any],
    group: Dict[str, Any],
    output_dir: Path,
    padding: float,
    scale: float = 2.0,
    open_crops: bool = False,
) -> Optional[Path]:
    """
    Создаёт composite crop непосредственно
    из исходной PDF-страницы.

    Вход:

        group["bbox"]

    находится в PDF points.

    Результат:

        PNG composite crop.
    """

    if pdf_file is None:

        print()
        print(
            "    composite crop: "
            "SKIPPED — PDF not found"
        )

        return None

    pymupdf = require_pymupdf()

    if pymupdf is None:

        return None

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    page_no = page_number(
        page,
        0,
    )

    group_id = get_group_id(
        group
    )

    bbox = group.get(
        "bbox"
    )

    if not bbox or len(bbox) != 4:

        members = resolve_group_members(
            page,
            group,
        )

        bbox = calculate_group_bbox(
            members
        )

    if not bbox:

        print()
        print(
            "    composite crop: "
            "SKIPPED — group bbox unavailable"
        )

        return None

    document = None

    try:

        document = pymupdf.open(
            str(pdf_file)
        )

        if page_no < 1:

            raise ValueError(
                f"Некорректный номер страницы: "
                f"{page_no}"
            )

        if page_no > len(document):

            raise ValueError(
                f"PDF содержит "
                f"{len(document)} страниц, "
                f"а требуется page {page_no}"
            )

        pdf_page = document[
            page_no - 1
        ]

        crop_rect = calculate_pdf_crop_rect(
            pdf_page.rect,
            bbox,
            padding,
        )

        clip = pymupdf.Rect(
            crop_rect
        )

        matrix = pymupdf.Matrix(
            scale,
            scale,
        )

        pixmap = pdf_page.get_pixmap(
            matrix=matrix,
            clip=clip,
            alpha=False,
        )

        filename = (
            f"page_{page_no:03d}"
            f"_group_{group_id}"
            f"_composite.png"
        )

        output_path = (
            output_dir
            / filename
        )

        pixmap.save(
            str(output_path)
        )

        print()
        print(
            "    composite crop:"
        )

        print(
            f"        {output_path}"
        )

        print(
            f"        source bbox : "
            f"{fmt_bbox(bbox)}"
        )

        print(
            f"        PDF size    : "
            f"{bbox_width(bbox):.2f} x "
            f"{bbox_height(bbox):.2f} pt"
        )

        print(
            f"        crop rect   : "
            f"[{crop_rect[0]:.2f}, "
            f"{crop_rect[1]:.2f}, "
            f"{crop_rect[2]:.2f}, "
            f"{crop_rect[3]:.2f}]"
        )

        print(
            f"        padding     : "
            f"{padding:.2f} pt"
        )

        print(
            f"        scale       : "
            f"{scale:.2f}"
        )

        print(
            f"        image size  : "
            f"{pixmap.width} x "
            f"{pixmap.height} px"
        )

        print(
            f"        members     : "
            f"{len(resolve_group_members(page, group))}"
        )

        if open_crops:

            open_file(
                output_path
            )

        return output_path

    except Exception as exc:

        print()
        print(
            "    composite crop: ERROR"
        )

        print(
            f"        {exc}"
        )

        return None

    finally:

        if document is not None:

            document.close()


def open_file(
    path: Path,
) -> None:
    """
    Открывает файл средствами ОС.
    """

    try:

        if os.name == "nt":

            os.startfile(
                str(path)
            )  # type: ignore[attr-defined]

        elif sys.platform == "darwin":

            subprocess.Popen(
                [
                    "open",
                    str(path),
                ]
            )

        else:

            subprocess.Popen(
                [
                    "xdg-open",
                    str(path),
                ]
            )

    except Exception as exc:

        print(
            f"    Не удалось открыть "
            f"{path}: {exc}"
        )


# ============================================================================
# JSON DIAGNOSTICS
# ============================================================================


def build_json_member(
    semantic_file: Path,
    element: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "parser_index": element.get(
            "parser_index"
        ),

        "source_index": element.get(
            "source_index"
        ),

        "xref": element.get(
            "xref"
        ),

        "type": element.get(
            "type"
        ),

        "element_type": element.get(
            "element_type"
        ),

        "semantic_role": element.get(
            "semantic_role"
        ),

        "bbox": element.get(
            "bbox"
        ),

        "classification": get_classification(
            element
        ),
    }


def build_json_group(
    semantic_file: Path,
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> Dict[str, Any]:

    group_id = get_group_id(
        group
    )

    members = resolve_group_members(
        page,
        group,
    )

    declared_members = group.get(
        "parser_indices",
        [],
    )

    if not isinstance(
        declared_members,
        list,
    ):

        declared_count = 0

    else:

        declared_count = len(
            declared_members
        )

    decision = calculate_group_decision(
        members
    )

    return {
        "version": VERSION,

        "semantic_file": str(
            semantic_file
        ),

        "page": page_number(
            page,
            0,
        ),

        "group_id": group_id,

        "members_declared": declared_count,

        "members_resolved": len(
            members
        ),

        "composite": bool(
            group.get(
                "composite"
            )
        ),

        "confidence": group.get(
            "confidence"
        ),

        "parser_indices": group.get(
            "parser_indices",
            [],
        ),

        "source_indices": group.get(
            "source_indices",
            [],
        ),

        "xrefs": group.get(
            "xrefs",
            [],
        ),

        "bbox": group.get(
            "bbox"
        ),

        "members": [
            build_json_member(
                semantic_file,
                element,
            )
            for element in members
        ],

        "decision": decision,
    }


def print_json_diagnostics(
    groups: Sequence[
        Dict[str, Any]
    ],
) -> None:

    payload = {
        "version": VERSION,
        "groups": list(
            groups
        ),
    }

    print()
    print(
        "=" * 80
    )

    print(
        "JSON DIAGNOSTICS"
    )

    print(
        "=" * 80
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


# ============================================================================
# GROUP PRINT
# ============================================================================


def print_group(
    semantic_file: Path,
    page: Dict[str, Any],
    group: Dict[str, Any],
    geometry: bool,
    crops: bool,
    crop_padding: float,
    crop_dir: Path,
    pdf_file: Optional[Path],
    open_crops: bool,
) -> Tuple[
    List[Path],
    Optional[Path],
    Dict[str, Any],
]:

    group_id = get_group_id(
        group
    )

    members = resolve_group_members(
        page,
        group,
    )

    declared_members = group.get(
        "parser_indices",
        [],
    )

    if not isinstance(
        declared_members,
        list,
    ):

        declared_count = 0

    else:

        declared_count = len(
            declared_members
        )

    current_page = page_number(
        page,
        0,
    )

    print()
    print(
        "=" * 80
    )

    print(
        f"PAGE {current_page} / "
        f"GROUP {group_id}"
    )

    print(
        "=" * 80
    )

    print(
        f"members declared : "
        f"{declared_count}"
    )

    print(
        f"members resolved : "
        f"{len(members)}"
    )

    print(
        f"composite        : "
        f"{group.get('composite')}"
    )

    print(
        f"confidence       : "
        f"{group.get('confidence')}"
    )

    print(
        f"parser_indices   : "
        f"{group.get('parser_indices')}"
    )

    print(
        f"source_indices   : "
        f"{group.get('source_indices')}"
    )

    print(
        f"xrefs            : "
        f"{group.get('xrefs')}"
    )

    print(
        f"bbox             : "
        f"{fmt_bbox(group.get('bbox'))}"
    )

    print_formula_relations(
        page,
        group_id,
    )

    if geometry:

        print_group_geometry(
            members,
            group.get(
                "bbox"
            ),
        )

    print()
    print(
        "ELEMENTS:"
    )

    for position, element in enumerate(
        members,
        start=1,
    ):

        print_element(
            semantic_file,
            element,
            position,
        )

    print_distributions(
        members
    )

    if geometry:

        print_pairwise_geometry(
            members
        )

    decision = print_group_decision(
        members
    )

    generated_elements = []
    generated_composite = None

    if crops:

        print()
        print(
            "CROPS"
        )

        print(
            "-" * 80
        )

        generated_elements = crop_group_images(
            semantic_file=semantic_file,
            page=page,
            group=group,
            output_dir=crop_dir,
            padding=0.0,
            open_crops=False,
        )

        generated_composite = (
            crop_group_from_pdf(
                pdf_file=pdf_file,
                page=page,
                group=group,
                output_dir=crop_dir,
                padding=crop_padding,
                scale=2.0,
                open_crops=open_crops,
            )
        )

        if open_crops:

            for path in generated_elements:

                open_file(
                    path
                )

    json_group = build_json_group(
        semantic_file,
        page,
        group,
    )

    return (
        generated_elements,
        generated_composite,
        json_group,
    )


# ============================================================================
# ARGUMENTS
# ============================================================================


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "VKS Expert AI — "
            "Formula Group Diagnostics"
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--page",
        type=int,
        help="Номер страницы.",
    )

    parser.add_argument(
        "--group",
        type=int,
        help="ID группы.",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Показать все "
            "unnumbered composite groups."
        ),
    )

    parser.add_argument(
        "--geometry",
        action="store_true",
        help=(
            "Показать подробную "
            "геометрическую диагностику."
        ),
    )

    parser.add_argument(
        "--crops",
        "--crop",
        dest="crops",
        action="store_true",
        help=(
            "Создать crops "
            "элементов и composite crop. "
            "Доступны --crops и --crop."
        ),
    )

    parser.add_argument(
        "--open-crops",
        action="store_true",
        help=(
            "После создания crops "
            "открыть их."
        ),
    )

    parser.add_argument(
        "--crop-padding",
        type=float,
        default=0.0,
        help=(
            "Дополнительный padding "
            "composite crop в PDF points. "
            "По умолчанию: 0."
        ),
    )

    parser.add_argument(
        "--crop-dir",
        type=Path,
        default=(
            Path("knowledge")
            / "parsed"
            / "diagnostics"
            / "formula_crops"
        ),
        help=(
            "Каталог для crops."
        ),
    )

    parser.add_argument(
        "--pdf-file",
        type=Path,
        default=None,
        help=(
            "Путь к исходному PDF. "
            "Если не указан, PDF ищется автоматически."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help=(
            "Количество групп при --all. "
            "По умолчанию: 5."
        ),
    )

    parser.add_argument(
        "--semantic-file",
        type=Path,
        default=DEFAULT_SEMANTIC_FILE,
        help=(
            "Путь к semantic JSON."
        ),
    )

    return parser


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:

    parser = build_parser()

    args = parser.parse_args()

    semantic_file = args.semantic_file

    data = load_json(
        semantic_file
    )

    pages = get_pages(
        data
    )

    candidates = (
        get_unnumbered_composite_groups(
            data
        )
    )

    print_header(
        semantic_file=semantic_file,
        pages=pages,
        unnumbered_count=len(
            candidates
        ),
    )

    pdf_file, pdf_status = resolve_pdf_file(
        semantic_file=semantic_file,
        explicit_pdf=args.pdf_file,
    )

    print_pdf_source(
        semantic_file=semantic_file,
        pdf_file=pdf_file,
        pdf_status=pdf_status,
    )

    # ------------------------------------------------------------------------
    # SELECT GROUPS
    # ------------------------------------------------------------------------

    selected = []

    for (
        current_page,
        page,
        group,
    ) in candidates:

        group_id = get_group_id(
            group
        )

        if args.page is not None:

            if current_page != args.page:
                continue

        if args.group is not None:

            if group_id != args.group:
                continue

        selected.append(
            (
                current_page,
                page,
                group,
            )
        )

    if not args.all:

        if (
            args.page is None
            and args.group is None
        ):

            selected = selected[
                : max(
                    0,
                    args.limit,
                )
            ]

    else:

        selected = selected[
            : max(
                0,
                args.limit,
            )
        ]

    print()
    print(
        f"Selected groups: "
        f"{len(selected)}"
    )

    if not selected:

        print()
        print(
            "Группы не найдены."
        )

        if args.page is not None:

            print(
                f"    page={args.page}"
            )

        if args.group is not None:

            print(
                f"    group={args.group}"
            )

        return

    # ------------------------------------------------------------------------
    # PROCESS
    # ------------------------------------------------------------------------

    generated_element_crops: List[
        Path
    ] = []

    generated_composite_crops: List[
        Path
    ] = []

    json_groups = []

    for (
        current_page,
        page,
        group,
    ) in selected:

        (
            generated_elements,
            generated_composite,
            json_group,
        ) = print_group(
            semantic_file=semantic_file,
            page=page,
            group=group,
            geometry=args.geometry,
            crops=args.crops,
            crop_padding=args.crop_padding,
            crop_dir=args.crop_dir,
            pdf_file=pdf_file,
            open_crops=args.open_crops,
        )

        generated_element_crops.extend(
            generated_elements
        )

        if generated_composite:

            generated_composite_crops.append(
                generated_composite
            )

        json_groups.append(
            json_group
        )

    # ------------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------------

    print()
    print(
        "=" * 80
    )

    if args.crops:

        print(
            f"Generated element crops: "
            f"{len(generated_element_crops)}"
        )

        print(
            f"Generated composite crops: "
            f"{len(generated_composite_crops)}"
        )

        print(
            f"Generated crops total: "
            f"{len(generated_element_crops) + len(generated_composite_crops)}"
        )

        print(
            f"Crop directory: "
            f"{args.crop_dir}"
        )

    print(
        f"Diagnostic groups: "
        f"{len(json_groups)}"
    )

    print(
        "=" * 80
    )

    print_json_diagnostics(
        json_groups
    )


if __name__ == "__main__":
    main()
    