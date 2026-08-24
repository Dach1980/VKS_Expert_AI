#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VKS Expert AI — Semantic PDF Parser

Точка входа совместима с двумя способами запуска:

    python -m app.semantic_parser

и:

    python app/semantic_parser.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# ============================================================================
# PROJECT ROOT
# ============================================================================

# semantic_parser.py находится:
#
# VKS_Expert_AI/
# └── app/
#     └── semantic_parser.py
#
# Поэтому родительский каталог app — это корень проекта.

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Добавляем корень проекта в sys.path,
# если скрипт запущен напрямую.
#
# Это позволяет Python найти пакет:
#
# app.semantic
#
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# IMPORT
# ============================================================================

from app.semantic.cli import main


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
    