"""
VKS Expert AI — main application entry point.
"""

from __future__ import annotations

import sys


def main() -> None:
    """
    Главная точка входа VKS Expert AI.

    На текущем этапе поддерживается semantic parser.
    Архитектура позволяет позднее добавить:

        pdf
        semantic
        knowledge
        rag
        llm

    как отдельные команды.
    """

    if len(sys.argv) == 1:
        from app.semantic.cli import main as semantic_main

        semantic_main()
        return

    command = sys.argv[1]

    if command == "semantic":
        from app.semantic.cli import main as semantic_main

        # Убираем "semantic" перед передачей аргументов.
        sys.argv.pop(1)

        semantic_main()
        return

    print(
        "VKS Expert AI"
    )

    print()
    print(
        "Доступная команда:"
    )

    print(
        "  python -m app.main semantic parse"
    )


if __name__ == "__main__":
    main()
    