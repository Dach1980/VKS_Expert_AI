"""
VKS Expert AI — command line interface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    DEBUG_PAGE,
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    VERSION,
)

from .debug import debug_page
from .pipeline import process_page
from .source import get_pages
from .statistics import build_statistics
from .validation import validate_page_result


def parse_document(
    source_path: Path,
    output_path: Path,
) -> None:

    print("=" * 80)

    print(
        f"VKS Expert AI — "
        f"Semantic PDF Parser v{VERSION}"
    )

    print("=" * 80)
    print()

    print(
        f"Источник:\n{source_path}"
    )

    print()

    print(
        "Загрузка elements.json..."
    )

    with source_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        source = json.load(file)

    pages = get_pages(source)

    print(
        f"Страниц: {len(pages)}"
    )

    print()

    print(
        "Семантический анализ..."
    )

    semantic_pages = []

    validation_errors = []

    debug_result = None

    for page_position, page in enumerate(pages):

        page_number = page.get(
            "page_number",
            page_position + 1,
        )

        print(
            f"Обработка страницы "
            f"{page_number}..."
        )

        page_result = process_page(
            page,
            page_number,
        )

        semantic_pages.append(
            page_result
        )

        page_errors = validate_page_result(
            page_result
        )

        for error in page_errors:

            validation_errors.append(
                f"page={page_number}: {error}"
            )

        if page_number == DEBUG_PAGE:

            debug_result = page_result

    statistics = build_statistics(
        semantic_pages,
        validation_errors,
    )

    result = {
        "parser": {
            "name":
                "VKS Expert AI "
                "Semantic PDF Parser",

            "version":
                VERSION,
        },

        "source":
            str(source_path),

        "statistics":
            statistics,

        "pages":
            semantic_pages,

        "validation": {
            "valid":
                len(validation_errors) == 0,

            "errors":
                validation_errors,
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    if debug_result is not None:

        debug_page(
            DEBUG_PAGE,
            debug_result,
        )

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)
    print()

    print(
        "Результат:"
    )

    print(output_path)

    print()

    print("СТАТИСТИКА")

    print("-" * 80)

    labels = [
        ("Страниц", "pages"),
        ("Элементов", "elements"),
        ("Изображений", "images"),
        ("Символов", "symbols"),
        ("Фрагментов формул", "formula_fragments"),
        ("Кандидатов схем", "diagram_candidates"),
        ("Кандидатов формул", "formula_candidates"),
        ("Групп формул", "formula_groups"),
        ("Составных групп", "composite_groups"),
        ("Номеров формул", "formula_numbers"),
        ("Связанных формул", "formula_relations"),
        ("Формул без номера", "formulas_without_number"),
        ("Ошибок валидации", "validation_errors"),
    ]

    for label, key in labels:

        print(
            f"{label + ':':<30}"
            f"{statistics[key]:>10}"
        )

    print()

    if validation_errors:

        print(
            "ПЕРВЫЕ ОШИБКИ ВАЛИДАЦИИ"
        )

        print("-" * 80)

        for error in validation_errors[:20]:

            print(
                f"  {error}"
            )

        if len(validation_errors) > 20:

            print(
                f"... и ещё "
                f"{len(validation_errors) - 20}"
            )

    else:

        print(
            "Валидация: OK"
        )


def main() -> None:

    import sys

    if len(sys.argv) >= 2:

        source_path = Path(
            sys.argv[1]
        )

    else:

        source_path = DEFAULT_SOURCE

    if len(sys.argv) >= 3:

        output_path = Path(
            sys.argv[2]
        )

    else:

        output_path = DEFAULT_OUTPUT

    if not source_path.exists():

        print("ОШИБКА:")

        print(
            f"Файл не найден:\n"
            f"{source_path}"
        )

        sys.exit(1)

    parse_document(
        source_path,
        output_path,
    )
    