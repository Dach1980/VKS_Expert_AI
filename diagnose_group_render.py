"""
VKS Expert AI — Formula Group Render Diagnostics v0.1.1

Рендер исходной PDF-страницы с визуальным выделением
bbox составной группы формул.

v0.1.1
------

Изменения относительно v0.1.0:

    • улучшен автоматический поиск исходного PDF;
    • PDF больше не обязан называться точно как semantic JSON;
    • поддерживаются PDF внутри каталогов документа;
    • для SP_30.13330.2020.semantic.json может быть найден:
          knowledge/regulations/SP_30.13330/
          СП_30.13330_базовая_версия.pdf
    • добавлен вывод найденного PDF;
    • добавлена визуализация bbox группы;
    • добавлена визуализация bbox отдельных элементов;
    • добавлена подпись группы;
    • добавлена защита bbox от выхода за границы страницы;
    • сохранён fallback: group bbox -> calculated bbox;
    • сохранён явный --pdf-file;
    • добавлен --output;
    • добавлен --scale;
    • добавлен --padding;
    • добавлен --elements;
    • добавлен --open;
    • диагностический инструмент ничего не изменяет в semantic JSON.

Примеры:

    python diagnose_group_render.py --page 12 --group 13

    python diagnose_group_render.py --page 12 --group 13 --elements

    python diagnose_group_render.py --page 12 --group 13 --padding 10

    python diagnose_group_render.py --page 12 --group 13 --scale 2

    python diagnose_group_render.py --page 12 --group 13 --elements --open

    python diagnose_group_render.py --page 12 --group 13 ^
        --pdf-file "knowledge\\regulations\\SP_30.13330\\СП_30.13330_базовая_версия.pdf"

    python diagnose_group_render.py --all --limit 5
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


VERSION = "0.1.1"


DEFAULT_SEMANTIC_FILE = (
    Path("knowledge")
    / "parsed"
    / "SP_30.13330.2020.semantic.json"
)

DEFAULT_OUTPUT_DIR = (
    Path("knowledge")
    / "parsed"
    / "diagnostics"
    / "formula_renders"
)


# ============================================================================
# BASIC HELPERS
# ============================================================================


def safe_int(
    value: Any,
) -> Optional[int]:
    """Безопасно преобразует значение в int."""

    try:
        return int(value)

    except (TypeError, ValueError):

        return None


def safe_float(
    value: Any,
) -> Optional[float]:
    """Безопасно преобразует значение в float."""

    try:
        return float(value)

    except (TypeError, ValueError):

        return None


def fmt_number(
    value: Any,
    digits: int = 2,
) -> str:
    """Форматирует число."""

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

    return (
        float(bbox[2])
        - float(bbox[0])
    )


def bbox_height(
    bbox: Sequence[Any],
) -> float:

    return (
        float(bbox[3])
        - float(bbox[1])
    )


# ============================================================================
# JSON
# ============================================================================


def load_json(
    path: Path,
) -> Dict[str, Any]:
    """Загружает semantic JSON."""

    if not path.exists():

        print()
        print(
            "ERROR: semantic JSON не найден."
        )

        print(
            f"    {path}"
        )

        print()

        sys.exit(1)

    try:

        import json

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except Exception as exc:

        print()
        print(
            "ERROR: не удалось загрузить semantic JSON."
        )

        print(
            f"    {path}"
        )

        print(
            f"    {exc}"
        )

        print()

        sys.exit(1)

    if not isinstance(data, dict):

        print()
        print(
            "ERROR: корень semantic JSON "
            "должен быть объектом."
        )

        print()

        sys.exit(1)

    return data


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

    return [
        page
        for page in pages
        if isinstance(
            page,
            dict,
        )
    ]


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

    if parsed is None:

        return fallback

    return parsed


# ============================================================================
# BBOX
# ============================================================================


def valid_bbox(
    bbox: Any,
) -> bool:

    if not isinstance(
        bbox,
        (list, tuple),
    ):

        return False

    if len(bbox) != 4:

        return False

    values = []

    for value in bbox:

        parsed = safe_float(
            value
        )

        if parsed is None:

            return False

        values.append(
            parsed
        )

    return (
        values[2] > values[0]
        and values[3] > values[1]
    )


def calculate_group_bbox(
    members: Sequence[Dict[str, Any]],
) -> Optional[List[float]]:
    """
    Рассчитывает bbox группы по bbox элементов.
    """

    boxes = [
        element.get("bbox")
        for element in members
        if valid_bbox(
            element.get("bbox")
        )
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
# GROUP RESOLUTION
# ============================================================================


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


def resolve_group_members(
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Восстанавливает элементы группы
    по parser_indices.
    """

    elements = page.get(
        "elements",
        [],
    )

    if not isinstance(
        elements,
        list,
    ):

        return []

    by_parser_index = {}

    for element in elements:

        if not isinstance(
            element,
            dict,
        ):

            continue

        parser_index = safe_int(
            element.get(
                "parser_index"
            )
        )

        if parser_index is not None:

            by_parser_index[
                parser_index
            ] = element

    parser_indices = group.get(
        "parser_indices",
        [],
    )

    if not isinstance(
        parser_indices,
        list,
    ):

        return []

    result = []

    for parser_index in parser_indices:

        parsed_index = safe_int(
            parser_index
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


def find_page(
    data: Dict[str, Any],
    requested_page: int,
) -> Optional[Dict[str, Any]]:

    pages = get_pages(
        data
    )

    for fallback, page in enumerate(
        pages,
        start=1,
    ):

        current = page_number(
            page,
            fallback,
        )

        if current == requested_page:

            return page

    return None


def find_group(
    page: Dict[str, Any],
    requested_group: int,
) -> Optional[Dict[str, Any]]:

    groups = page.get(
        "formula_groups",
        [],
    )

    if not isinstance(
        groups,
        list,
    ):

        return None

    for group in groups:

        if not isinstance(
            group,
            dict,
        ):

            continue

        group_id = get_group_id(
            group
        )

        if group_id != requested_group:

            continue

        return group

    return None


# ============================================================================
# PDF NAME / SEARCH
# ============================================================================


def semantic_pdf_basename(
    semantic_file: Path,
) -> str:
    """
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


def normalize_name(
    value: str,
) -> str:
    """
    Нормализует имя для приблизительного
    сравнения.
    """

    value = value.lower()

    replacements = [
        " ",
        "_",
        "-",
        ".",
        "(",
        ")",
        "[",
        "]",
    ]

    for char in replacements:

        value = value.replace(
            char,
            "",
        )

    return value


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

        seen.add(
            key
        )

        result.append(
            path
        )

    return result


def pdf_score(
    pdf: Path,
    semantic_file: Path,
) -> int:
    """
    Рассчитывает приблизительный рейтинг PDF.

    Чем больше score, тем вероятнее,
    что PDF является исходным документом.

    Приоритет:

        exact semantic basename
        basename fragment
        совпадение каталога документа
        совпадение частей имени
        стандартные каталоги knowledge
    """

    score = 0

    semantic_basename = semantic_pdf_basename(
        semantic_file
    )

    semantic_norm = normalize_name(
        semantic_basename
    )

    pdf_stem_norm = normalize_name(
        pdf.stem
    )

    semantic_parts = [
        part
        for part in semantic_basename.lower().replace(
            "_",
            ".",
        ).split(".")
        if part
    ]

    pdf_lower = pdf.stem.lower()

    # ------------------------------------------------------------------------
    # Exact-ish filename match
    # ------------------------------------------------------------------------

    if pdf_stem_norm == semantic_norm:

        score += 1000

    if semantic_norm in pdf_stem_norm:

        score += 500

    if pdf_stem_norm in semantic_norm:

        score += 300

    # ------------------------------------------------------------------------
    # Important document identifier
    # ------------------------------------------------------------------------

    for part in semantic_parts:

        if len(part) < 3:

            continue

        if part in pdf_lower:

            score += 50

    # ------------------------------------------------------------------------
    # Parent directory
    # ------------------------------------------------------------------------

    parent_text = " ".join(
        part.lower()
        for part in pdf.parts
    )

    if "sp_30.13330" in parent_text:

        score += 250

    if "30.13330" in parent_text:

        score += 100

    if "regulations" in parent_text:

        score += 50

    if "source" in parent_text:

        score += 40

    # ------------------------------------------------------------------------
    # Known semantic file neighborhood
    # ------------------------------------------------------------------------

    try:

        semantic_parent = semantic_file.parent.resolve()

        pdf_resolved = pdf.resolve()

        if semantic_parent in pdf_resolved.parents:

            score += 100

    except Exception:

        pass

    return score


def find_pdf_candidates(
    semantic_file: Path,
) -> List[Path]:
    """
    Ищет PDF в проекте.

    В отличие от v0.1.0 поиск не ограничивается
    одним конкретным именем.
    """

    project_root = Path.cwd()

    candidates = []

    # ------------------------------------------------------------------------
    # 1. PDF рядом с semantic JSON
    # ------------------------------------------------------------------------

    semantic_basename = semantic_pdf_basename(
        semantic_file
    )

    candidates.extend(
        [
            semantic_file.parent
            / f"{semantic_basename}.pdf",

            semantic_file.parent.parent
            / f"{semantic_basename}.pdf",

            semantic_file.parent.parent
            / "source"
            / f"{semantic_basename}.pdf",

            semantic_file.parent.parent
            / "regulations"
            / f"{semantic_basename}.pdf",
        ]
    )

    # ------------------------------------------------------------------------
    # 2. Standard knowledge directories
    # ------------------------------------------------------------------------

    knowledge = (
        project_root
        / "knowledge"
    )

    standard_directories = [
        knowledge,
        knowledge / "source",
        knowledge / "regulations",
        knowledge / "parsed",
    ]

    for directory in standard_directories:

        if not directory.exists():

            continue

        try:

            candidates.extend(
                directory.rglob(
                    "*.pdf"
                )
            )

        except Exception:

            pass

    # ------------------------------------------------------------------------
    # 3. Project-wide fallback
    # ------------------------------------------------------------------------

    try:

        candidates.extend(
            project_root.rglob(
                "*.pdf"
            )
        )

    except Exception:

        pass

    candidates = unique_paths(
        candidates
    )

    existing = [
        path
        for path in candidates
        if path.exists()
        and path.is_file()
    ]

    return existing


def resolve_pdf_file(
    semantic_file: Path,
    explicit_pdf: Optional[Path],
) -> Tuple[
    Optional[Path],
    str,
    List[Tuple[Path, int]],
]:
    """
    Определяет исходный PDF.

    Приоритет:

        1. --pdf-file
        2. автоматический поиск
        3. ranking найденных PDF
    """

    # ------------------------------------------------------------------------
    # Explicit
    # ------------------------------------------------------------------------

    if explicit_pdf is not None:

        explicit_candidates = []

        if explicit_pdf.is_absolute():

            explicit_candidates.append(
                explicit_pdf
            )

        else:

            explicit_candidates.extend(
                [
                    Path.cwd()
                    / explicit_pdf,

                    explicit_pdf,
                ]
            )

        explicit_candidates = unique_paths(
            explicit_candidates
        )

        for candidate in explicit_candidates:

            if (
                candidate.exists()
                and candidate.is_file()
            ):

                return (
                    candidate.resolve(),
                    "EXPLICIT",
                    [
                        (
                            candidate.resolve(),
                            10000,
                        )
                    ],
                )

        return (
            None,
            "EXPLICIT_NOT_FOUND",
            [],
        )

    # ------------------------------------------------------------------------
    # Automatic search
    # ------------------------------------------------------------------------

    candidates = find_pdf_candidates(
        semantic_file
    )

    ranked = []

    for candidate in candidates:

        score = pdf_score(
            candidate,
            semantic_file,
        )

        ranked.append(
            (
                candidate,
                score,
            )
        )

    ranked.sort(
        key=lambda item: (
            item[1],
            str(item[0]).lower(),
        ),
        reverse=True,
    )

    if not ranked:

        return (
            None,
            "NOT_FOUND",
            [],
        )

    best_path, best_score = ranked[0]

    # ------------------------------------------------------------------------
    # Ambiguity protection
    # ------------------------------------------------------------------------

    if best_score <= 0:

        return (
            None,
            "NOT_CONFIDENT",
            ranked,
        )

    return (
        best_path.resolve(),
        "AUTO",
        ranked,
    )


# ============================================================================
# PDF OUTPUT
# ============================================================================


def print_pdf_source(
    semantic_file: Path,
    pdf_file: Optional[Path],
    status: str,
    candidates: Sequence[
        Tuple[Path, int]
    ],
) -> None:

    print()
    print(
        "PDF SOURCE"
    )

    print(
        "-" * 80
    )

    print(
        f"    semantic file : "
        f"{semantic_file}"
    )

    print(
        f"    semantic base : "
        f"{semantic_pdf_basename(semantic_file)}"
    )

    print(
        f"    status        : "
        f"{status}"
    )

    if pdf_file:

        print(
            f"    resolved PDF  : "
            f"{pdf_file}"
        )

    else:

        print(
            "    resolved PDF  : NOT FOUND"
        )

    if candidates:

        print()
        print(
            "    PDF candidates:"
        )

        for path, score in candidates[:10]:

            marker = (
                " <-- SELECTED"
                if pdf_file is not None
                and path.resolve() == pdf_file.resolve()
                else ""
            )

            print(
                f"        [{score:4d}] "
                f"{path}"
                f"{marker}"
            )


# ============================================================================
# CROP RECT
# ============================================================================


def calculate_crop_rect(
    page_rect: Any,
    bbox: Sequence[Any],
    padding: float,
) -> Tuple[
    float,
    float,
    float,
    float,
]:
    """
    Рассчитывает bbox crop в координатах PDF.

    Защищает прямоугольник от выхода
    за пределы страницы.
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

        x1 = min(
            float(page_rect.x1),
            x0 + 1.0,
        )

    if y1 <= y0:

        y1 = min(
            float(page_rect.y1),
            y0 + 1.0,
        )

    return (
        x0,
        y0,
        x1,
        y1,
    )


# ============================================================================
# RENDER
# ============================================================================


def require_pymupdf() -> Any:

    try:

        import pymupdf

        return pymupdf

    except ImportError:

        print()
        print(
            "ERROR: PyMuPDF не установлен."
        )

        print()
        print(
            "Установите:"
        )

        print(
            "    pip install pymupdf"
        )

        print()

        return None


def render_group(
    pdf_file: Path,
    page: Dict[str, Any],
    group: Dict[str, Any],
    output_dir: Path,
    scale: float,
    padding: float,
    draw_elements: bool,
) -> Optional[Path]:
    """
    Рендерит исходную PDF-страницу.

    На странице рисуется:

        красный прямоугольник = group bbox

        синие прямоугольники = element bbox

    Результат сохраняется как PNG.
    """

    pymupdf = require_pymupdf()

    if pymupdf is None:

        return None

    page_no = page_number(
        page,
        0,
    )

    group_id = get_group_id(
        group
    )

    if page_no <= 0:

        print()
        print(
            "ERROR: некорректный номер страницы."
        )

        return None

    members = resolve_group_members(
        page,
        group,
    )

    group_bbox = group.get(
        "bbox"
    )

    if not valid_bbox(
        group_bbox
    ):

        group_bbox = calculate_group_bbox(
            members
        )

    if not valid_bbox(
        group_bbox
    ):

        print()
        print(
            "ERROR: bbox группы отсутствует."
        )

        print(
            "       Также не удалось "
            "рассчитать bbox по элементам."
        )

        return None

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    document = None

    try:

        document = pymupdf.open(
            str(pdf_file)
        )

        if page_no > len(document):

            raise ValueError(
                f"PDF содержит {len(document)} страниц, "
                f"а требуется page {page_no}"
            )

        pdf_page = document[
            page_no - 1
        ]

        page_rect = pdf_page.rect

        # --------------------------------------------------------------------
        # Crop / render area
        # --------------------------------------------------------------------

        crop_rect = calculate_crop_rect(
            page_rect,
            group_bbox,
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

        # --------------------------------------------------------------------
        # Annotation page
        # --------------------------------------------------------------------

        shape = pdf_page.new_shape()

        group_rect = pymupdf.Rect(
            group_bbox
        )

        shape.draw_rect(
            group_rect
        )

        shape.finish(
            color=(1, 0, 0),
            width=2.0,
            fill=None,
        )

        shape.commit()

        # --------------------------------------------------------------------
        # Element rectangles
        # --------------------------------------------------------------------

        if draw_elements:

            for position, element in enumerate(
                members,
                start=1,
            ):

                element_bbox = element.get(
                    "bbox"
                )

                if not valid_bbox(
                    element_bbox
                ):

                    continue

                element_rect = pymupdf.Rect(
                    element_bbox
                )

                element_shape = (
                    pdf_page.new_shape()
                )

                element_shape.draw_rect(
                    element_rect
                )

                element_shape.finish(
                    color=(0, 0, 1),
                    width=1.0,
                    fill=None,
                )

                element_shape.commit()

                # ------------------------------------------------------------
                # Element label
                # ------------------------------------------------------------

                parser_index = element.get(
                    "parser_index"
                )

                label = (
                    f"E{position}"
                    f" / p{parser_index}"
                )

                text_point = pymupdf.Point(
                    float(element_rect.x0),
                    max(
                        float(page_rect.y0) + 8,
                        float(element_rect.y0) - 2,
                    ),
                )

                pdf_page.insert_text(
                    text_point,
                    label,
                    fontsize=7,
                    color=(0, 0, 1),
                )

        # --------------------------------------------------------------------
        # Group label
        # --------------------------------------------------------------------

        group_label = (
            f"GROUP {group_id}"
            f"  /  PAGE {page_no}"
        )

        label_point = pymupdf.Point(
            float(group_bbox[0]),
            max(
                float(page_rect.y0) + 12,
                float(group_bbox[1]) - 6,
            ),
        )

        pdf_page.insert_text(
            label_point,
            group_label,
            fontsize=10,
            color=(1, 0, 0),
        )

        # --------------------------------------------------------------------
        # Render after annotations
        # --------------------------------------------------------------------

        pixmap = pdf_page.get_pixmap(
            matrix=matrix,
            clip=clip,
            alpha=False,
        )

        filename = (
            f"page_{page_no:03d}"
            f"_group_{group_id}"
            f"_render.png"
        )

        output_path = (
            output_dir
            / filename
        )

        pixmap.save(
            str(output_path)
        )

        # --------------------------------------------------------------------
        # Diagnostics
        # --------------------------------------------------------------------

        print()
        print(
            "RENDER"
        )

        print(
            "-" * 80
        )

        print(
            f"    page          : "
            f"{page_no}"
        )

        print(
            f"    group         : "
            f"{group_id}"
        )

        print(
            f"    members       : "
            f"{len(members)}"
        )

        print(
            f"    group bbox    : "
            f"{group_bbox}"
        )

        print(
            f"    crop rect     : "
            f"["
            f"{crop_rect[0]:.2f}, "
            f"{crop_rect[1]:.2f}, "
            f"{crop_rect[2]:.2f}, "
            f"{crop_rect[3]:.2f}"
            f"]"
        )

        print(
            f"    padding       : "
            f"{padding:.2f} pt"
        )

        print(
            f"    scale         : "
            f"{scale:.2f}"
        )

        print(
            f"    image size    : "
            f"{pixmap.width} x "
            f"{pixmap.height} px"
        )

        print(
            f"    output        : "
            f"{output_path}"
        )

        print()
        print(
            "    legend:"
        )

        print(
            "        RED  = group bbox"
        )

        if draw_elements:

            print(
                "        BLUE = element bbox"
            )

        return output_path

    except Exception as exc:

        print()
        print(
            "ERROR: render failed."
        )

        print(
            f"    {exc}"
        )

        return None

    finally:

        if document is not None:

            document.close()


# ============================================================================
# OPEN FILE
# ============================================================================


def open_file(
    path: Path,
) -> None:
    """Открывает файл средствами ОС."""

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

        print()
        print(
            "WARNING: не удалось открыть файл."
        )

        print(
            f"    {path}"
        )

        print(
            f"    {exc}"
        )


# ============================================================================
# PRINT GROUP
# ============================================================================


def print_group_info(
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> None:

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

    print()
    print(
        "=" * 80
    )

    print(
        f"PAGE {page_no} / GROUP {group_id}"
    )

    print(
        "=" * 80
    )

    print(
        f"    composite       : "
        f"{group.get('composite')}"
    )

    print(
        f"    confidence      : "
        f"{group.get('confidence')}"
    )

    print(
        f"    declared bbox   : "
        f"{fmt_bbox(group.get('bbox'))}"
    )

    calculated = calculate_group_bbox(
        members
    )

    print(
        f"    calculated bbox : "
        f"{fmt_bbox(calculated)}"
    )

    print(
        f"    members declared: "
        f"{len(group.get('parser_indices', []))}"
    )

    print(
        f"    members resolved : "
        f"{len(members)}"
    )

    if members:

        print()
        print(
            "    ELEMENT BBOXES"
        )

        print(
            "    " + "-" * 68
        )

        for position, element in enumerate(
            members,
            start=1,
        ):

            print(
                f"        E{position}"
                f" parser_index="
                f"{element.get('parser_index')}"
                f" bbox="
                f"{fmt_bbox(element.get('bbox'))}"
            )


# ============================================================================
# ARGUMENTS
# ============================================================================


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "VKS Expert AI — "
            "Formula Group Render Diagnostics"
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--page",
        type=int,
        help=(
            "Номер страницы."
        ),
    )

    parser.add_argument(
        "--group",
        type=int,
        help=(
            "ID группы."
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Отрендерить несколько "
            "composite groups."
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
        "--output",
        "--output-dir",
        dest="output_dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Каталог для результатов рендера."
        ),
    )

    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help=(
            "Масштаб PDF render. "
            "По умолчанию: 2.0."
        ),
    )

    parser.add_argument(
        "--padding",
        type=float,
        default=10.0,
        help=(
            "Padding вокруг bbox группы "
            "в PDF points. "
            "По умолчанию: 10."
        ),
    )

    parser.add_argument(
        "--elements",
        action="store_true",
        help=(
            "Показать bbox отдельных элементов "
            "синими прямоугольниками."
        ),
    )

    parser.add_argument(
        "--open",
        action="store_true",
        help=(
            "Открыть созданный PNG."
        ),
    )

    return parser


# ============================================================================
# GROUP SELECTION
# ============================================================================


def get_composite_groups(
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

    for fallback_page, page in enumerate(
        pages,
        start=1,
    ):

        current_page = page_number(
            page,
            fallback_page,
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

            if group_id is None:

                continue

            result.append(
                (
                    current_page,
                    page,
                    group,
                )
            )

    return result


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:

    parser = build_parser()

    args = parser.parse_args()

    # ------------------------------------------------------------------------
    # Validate scale / padding
    # ------------------------------------------------------------------------

    if args.scale <= 0:

        parser.error(
            "--scale должен быть > 0"
        )

    if args.padding < 0:

        parser.error(
            "--padding не может быть отрицательным"
        )

    # ------------------------------------------------------------------------
    # Semantic JSON
    # ------------------------------------------------------------------------

    semantic_file = args.semantic_file

    data = load_json(
        semantic_file
    )

    pages = get_pages(
        data
    )

    print()
    print(
        f"VKS Expert AI — "
        f"Formula Group Render Diagnostics "
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

    # ------------------------------------------------------------------------
    # Resolve PDF
    # ------------------------------------------------------------------------

    pdf_file, pdf_status, pdf_candidates = (
        resolve_pdf_file(
            semantic_file=semantic_file,
            explicit_pdf=args.pdf_file,
        )
    )

    print_pdf_source(
        semantic_file=semantic_file,
        pdf_file=pdf_file,
        status=pdf_status,
        candidates=pdf_candidates,
    )

    if pdf_file is None:

        print()
        print(
            "ERROR: исходный PDF не найден."
        )

        if pdf_status == "EXPLICIT_NOT_FOUND":

            print()
            print(
                "Указанный PDF не существует:"
            )

            print(
                f"    {args.pdf_file}"
            )

        elif pdf_status == "NOT_CONFIDENT":

            print()
            print(
                "PDF-файлы найдены, "
                "но не удалось уверенно "
                "определить исходный документ."
            )

            print()
            print(
                "Укажите PDF явно:"
            )

            print(
                "    python diagnose_group_render.py "
                "--page 12 --group 13 "
                "--pdf-file "
                "\"knowledge\\regulations\\SP_30.13330\\"
                "СП_30.13330_базовая_версия.pdf\""
            )

        else:

            print()
            print(
                "Укажите PDF явно:"
            )

            print(
                "    python diagnose_group_render.py "
                "--page 12 --group 13 "
                "--pdf-file "
                "\"knowledge\\regulations\\SP_30.13330\\"
                "СП_30.13330_базовая_версия.pdf\""
            )

        print()

        sys.exit(1)

    # ------------------------------------------------------------------------
    # Select groups
    # ------------------------------------------------------------------------

    selected = []

    if args.page is not None:

        page = find_page(
            data,
            args.page,
        )

        if page is None:

            print()
            print(
                f"ERROR: страница {args.page} "
                f"не найдена в semantic JSON."
            )

            sys.exit(1)

        if args.group is not None:

            group = find_group(
                page,
                args.group,
            )

            if group is None:

                print()
                print(
                    f"ERROR: group {args.group} "
                    f"не найдена на странице "
                    f"{args.page}."
                )

                sys.exit(1)

            if not group_is_composite(
                group
            ):

                print()
                print(
                    "WARNING: выбранная группа "
                    "не имеет composite=true."
                )

            selected.append(
                (
                    args.page,
                    page,
                    group,
                )
            )

        else:

            groups = page.get(
                "formula_groups",
                [],
            )

            if isinstance(
                groups,
                list,
            ):

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

                    selected.append(
                        (
                            args.page,
                            page,
                            group,
                        )
                    )

                    if len(selected) >= max(
                        0,
                        args.limit,
                    ):

                        break

    else:

        candidates = get_composite_groups(
            data
        )

        selected = candidates[
            : max(
                0,
                args.limit,
            )
        ]

    # ------------------------------------------------------------------------
    # No groups
    # ------------------------------------------------------------------------

    print()
    print(
        f"Selected groups: "
        f"{len(selected)}"
    )

    if not selected:

        print()
        print(
            "Группы для рендера не найдены."
        )

        return

    # ------------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------------

    generated = []

    for (
        current_page,
        page,
        group,
    ) in selected:

        print_group_info(
            page,
            group,
        )

        output_path = render_group(
            pdf_file=pdf_file,
            page=page,
            group=group,
            output_dir=args.output_dir,
            scale=args.scale,
            padding=args.padding,
            draw_elements=args.elements,
        )

        if output_path is not None:

            generated.append(
                output_path
            )

            if args.open:

                open_file(
                    output_path
                )

    # ------------------------------------------------------------------------
    # Final
    # ------------------------------------------------------------------------

    print()
    print(
        "=" * 80
    )

    print(
        f"Rendered groups : "
        f"{len(generated)}"
    )

    print(
        f"Output directory: "
        f"{args.output_dir}"
    )

    if generated:

        print()
        print(
            "Generated files:"
        )

        for path in generated:

            print(
                f"    {path}"
            )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()
    