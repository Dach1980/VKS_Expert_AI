"""
Compatibility launcher.

Старый запуск:

    python -m app.semantic_parser

теперь передаёт управление новому semantic CLI.
"""

from app.semantic.cli import main


if __name__ == "__main__":
    main()
    