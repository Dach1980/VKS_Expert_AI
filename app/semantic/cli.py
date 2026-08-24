"""
Command-line interface for Semantic PDF Parser v0.8.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .config import (
    DEFAULT_OUTPUT,
    DEFAULT_SOURCE,
    DEBUG_PAGE,
    PARSER_NAME,
    VERSION,
)

from .debug import debug_page

from .pipeline import (
    process_document_pages,
)

from .source import (
    get_pages,
    load_json,
    save_json,
)

from .statistics import (
    build_statistics,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vks-semantic",
        description=(
            "VKS Expert AI Semantic PDF Parser"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    parse_parser = subparsers.add_parser(
        "parse",
        help="Parse elements.json",
    )

    parse_parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Source elements.json",
    )

    parse_parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output semantic.json",
    )

    parse_parser.add_argument(
        "--debug-page",
        type=int,
        default=DEBUG_PAGE,
        help="Page for debug output",
    )

    return parser


def print_statistics(
    statistics: dict,
) -> None:
    print()
    print("СТАТИСТИКА")
    print("-" * 80)

    labels = [
        ("Страниц", "pages"),
        ("Элементов", "elements"),
        ("Изображений", "images"),
        ("Символов", "symbols"),
        (
            "Фрагментов формул",
            "formula_fragments",
        ),
        (
            "Кандидатов схем",
            "diagram_candidates",
        ),
        (
            "Кандидатов формул",
            "formula_candidates",
        ),
        (
            "Групп формул",
            "formula_groups",
        ),
        (
            "Составных групп",
            "composite_groups",
        ),
        (
            "Номеров формул",
            "formula_numbers",
        ),
        (
            "Связанных формул",
            "formula_relations",
        ),
        (
            "Формул без номера",
            "formulas_without_number",
        ),
        (
            "Ошибок валидации",
            "validation_errors",
        ),
    ]

    for label, key in labels:
        print(
            f"{label + ':':<30}"
            f"{statistics[key]:>10}"
        )


def parse_document(
    source_path: Path,
    output_path: Path,
    debug_page_number: Optional[int] = None,
) -> None:
    print("=" * 80)
    print(
        f"{PARSER_NAME} v{VERSION}"
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

    source = load_json(
        source_path
    )

    pages = get_pages(source)

    print(
        f"Страниц: {len(pages)}"
    )

    print()
    print(
        "Семантический анализ..."
    )

    (
        semantic_pages,
        validation_errors,
    ) = process_document_pages(
        pages
    )

    statistics = build_statistics(
        semantic_pages,
        validation_errors,
    )

    result = {
        "parser": {
            "name": PARSER_NAME,
            "version": VERSION,
        },

        "source": str(
            source_path
        ),

        "statistics": statistics,

        "pages": semantic_pages,

        "validation": {
            "valid": (
                len(validation_errors) == 0
            ),
            "errors": validation_errors,
        },
    }

    save_json(
        result,
        output_path,
    )

    # ---------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------

    if debug_page_number is not None:
        for page_result in semantic_pages:
            if (
                page_result["page_number"]
                == debug_page_number
            ):
                debug_page(
                    debug_page_number,
                    page_result,
                )
                break

    # ---------------------------------------------------------------
    # Final output
    # ---------------------------------------------------------------

    print()
    print("=" * 80)
    print("ГОТОВО")
    print("=" * 80)
    print()

    print("Результат:")
    print(output_path)

    print_statistics(
        statistics
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


def main(
    argv: Optional[list[str]] = None,
) -> None:
    parser = create_parser()

    args = parser.parse_args(argv)

    if args.command is None:
        args.command = "parse"
        args.source = DEFAULT_SOURCE
        args.output = DEFAULT_OUTPUT
        args.debug_page = DEBUG_PAGE

    source_path = Path(
        args.source
    )

    output_path = Path(
        args.output
    )

    if not source_path.exists():
        parser.error(
            f"Файл не найден:\n"
            f"{source_path}"
        )

    parse_document(
        source_path,
        output_path,
        args.debug_page,
    )


if __name__ == "__main__":
    main()
    