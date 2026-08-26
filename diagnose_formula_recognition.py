"""
VKS Expert AI — Formula Recognition Diagnostics v0.1.0

Диагностика распознавания математических формул
с помощью UniMERNet.

v0.1.0
------
Первая экспериментальная версия.

Назначение:

    semantic JSON
        ↓
    formula group
        ↓
    group members
        ↓
    element image crops
        ↓
    UniMERNet
        ↓
    LaTeX

Скрипт НЕ изменяет semantic JSON.

Основной тест:

    python diagnose_formula_recognition.py --page 12 --group 13

Дополнительно:

    python diagnose_formula_recognition.py --page 12 --group 13 --open

    python diagnose_formula_recognition.py --page 12 --group 13 --model-path "..."

    python diagnose_formula_recognition.py --all --limit 5

Важно:

    v0.1.0 работает именно с element image-файлами.

    Composite PDF render пока не используется
    для распознавания.

Следующий этап после проверки качества:

    LaTeX
        ↓
    MathML
        ↓
    нормализованное математическое представление
        ↓
    связь с пунктом СП
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


VERSION = "0.1.0"


DEFAULT_SEMANTIC_FILE = (
    Path("knowledge")
    / "parsed"
    / "SP_30.13330.2020.semantic.json"
)


# ============================================================================
# BASIC HELPERS
# ============================================================================


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


def fmt_bbox(
    bbox: Optional[Sequence[Any]],
) -> str:

    if not bbox or len(bbox) != 4:

        return "None"

    return (
        "["
        f"{float(bbox[0]):.2f}, "
        f"{float(bbox[1]):.2f}, "
        f"{float(bbox[2]):.2f}, "
        f"{float(bbox[3]):.2f}"
        "]"
    )


# ============================================================================
# JSON
# ============================================================================


def load_json(
    path: Path,
) -> Dict[str, Any]:

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

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as exc:

        print()
        print(
            "ERROR: некорректный JSON."
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
        if isinstance(page, dict)
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

    parsed = safe_int(
        value
    )

    if parsed is None:

        return fallback

    return parsed


# ============================================================================
# GROUPS
# ============================================================================


def get_group_id(
    group: Dict[str, Any],
) -> Optional[int]:

    return safe_int(
        group.get(
            "group_id"
        )
    )


def group_is_composite(
    group: Dict[str, Any],
) -> bool:

    return bool(
        group.get(
            "composite"
        )
    )


def resolve_group_members(
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Восстанавливает реальные элементы группы
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

    by_parser_index: Dict[
        int,
        Dict[str, Any],
    ] = {}

    for element in elements:

        if not isinstance(
            element,
            dict,
        ):

            continue

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

    if not isinstance(
        parser_indices,
        list,
    ):

        return []

    result = []

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
    Ищет исходный image-файл элемента.

    Приоритет:

        1. element["file"]
        2. xref
    """

    file_value = element.get(
        "file"
    )

    if file_value:

        candidate = Path(
            str(file_value)
        )

        candidates = [
            candidate,
            semantic_file.parent / candidate,
            semantic_file.parent.parent / candidate,
            Path.cwd() / candidate,
        ]

        for item in candidates:

            try:

                if item.exists() and item.is_file():

                    return item.resolve()

            except OSError:

                continue

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

        if candidate.exists() and candidate.is_file():

            return candidate.resolve()

    return None


# ============================================================================
# OPTIONAL IMAGE OPEN
# ============================================================================


def open_file(
    path: Path,
) -> None:

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
            f"WARNING: не удалось открыть "
            f"{path}: {exc}"
        )


# ============================================================================
# UNIMERNET
# ============================================================================


def load_unimernet(
    model_path: Optional[Path] = None,
) -> Any:
    """
    Загружает UniMERNet.

    В разных версиях окружения API пакета может
    отличаться. Поэтому здесь используется
    несколько вариантов импорта.

    Если подходящий API не найден,
    скрипт завершает работу с понятной ошибкой.
    """

    try:

        import unimernet

    except ImportError:

        print()
        print(
            "ERROR: UniMERNet не установлен."
        )

        print()
        print(
            "Установите в активном .venv:"
        )

        print(
            "    pip install unimernet"
        )

        print()

        sys.exit(1)

    # ------------------------------------------------------------------------
    # Попытка найти официальный high-level API.
    # ------------------------------------------------------------------------

    candidates = []

    for name in (
        "UniMERNet",
        "UniMERNetModel",
        "Model",
    ):

        cls = getattr(
            unimernet,
            name,
            None,
        )

        if cls is not None:

            candidates.append(
                cls
            )

    if candidates:

        cls = candidates[0]

        try:

            if model_path is not None:

                return cls(
                    model_path=str(
                        model_path
                    )
                )

            return cls()

        except TypeError:

            try:

                if model_path is not None:

                    return cls(
                        str(model_path)
                    )

                return cls()

            except Exception:
                pass

        except Exception:
            pass

    # ------------------------------------------------------------------------
    # Если high-level API отсутствует, пробуем
    # стандартные компоненты transformers.
    # ------------------------------------------------------------------------

    try:

        import torch
        from transformers import (
            AutoModel,
            AutoProcessor,
        )

    except ImportError:

        print()
        print(
            "ERROR: установлен пакет UniMERNet, "
            "но не найден совместимый API."
        )

        print()
        print(
            "Проверьте установку UniMERNet "
            "и transformers."
        )

        print()

        sys.exit(1)

    if model_path is None:

        print()
        print(
            "ERROR: не удалось определить "
            "модель UniMERNet автоматически."
        )

        print()
        print(
            "Укажите путь к модели:"
        )

        print(
            "    --model-path ..."
        )

        print()

        sys.exit(1)

    print()
    print(
        "Loading UniMERNet model..."
    )

    print(
        f"    model: {model_path}"
    )

    processor = AutoProcessor.from_pretrained(
        str(model_path),
        trust_remote_code=True,
    )

    model = AutoModel.from_pretrained(
        str(model_path),
        trust_remote_code=True,
    )

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    model = model.to(
        device
    )

    model.eval()

    return {
        "backend": "transformers",
        "processor": processor,
        "model": model,
        "device": device,
    }


# ============================================================================
# FORMULA RECOGNITION
# ============================================================================


def recognize_formula(
    recognizer: Any,
    image_path: Path,
) -> Dict[str, Any]:
    """
    Выполняет распознавание одной формулы.

    Возвращает диагностический результат.

    Важно:

        v0.1.0 допускает несколько вариантов API,
        поскольку задача этой версии — проверить
        сам recognition pipeline.
    """

    # ------------------------------------------------------------------------
    # High-level object API.
    # ------------------------------------------------------------------------

    methods = (
        "recognize",
        "recognize_formula",
        "predict",
        "infer",
    )

    for method_name in methods:

        method = getattr(
            recognizer,
            method_name,
            None,
        )

        if method is None:

            continue

        try:

            result = method(
                str(image_path)
            )

            return normalize_recognition_result(
                result
            )

        except TypeError:

            try:

                result = method(
                    image_path
                )

                return normalize_recognition_result(
                    result
                )

            except Exception:
                continue

        except Exception as exc:

            return {
                "success": False,
                "latex": None,
                "confidence": None,
                "error": str(exc),
            }

    # ------------------------------------------------------------------------
    # Transformers backend.
    # ------------------------------------------------------------------------

    if isinstance(
        recognizer,
        dict,
    ):

        processor = recognizer.get(
            "processor"
        )

        model = recognizer.get(
            "model"
        )

        device = recognizer.get(
            "device",
            "cpu",
        )

        if processor is None or model is None:

            return {
                "success": False,
                "latex": None,
                "confidence": None,
                "error": (
                    "Некорректный UniMERNet "
                    "transformers backend."
                ),
            }

        try:

            from PIL import Image

            image = Image.open(
                image_path
            ).convert(
                "RGB"
            )

            inputs = processor(
                images=image,
                return_tensors="pt",
            )

            inputs = {
                key: value.to(device)
                for key, value in inputs.items()
            }

            generated = model.generate(
                **inputs
            )

            decoded = processor.batch_decode(
                generated,
                skip_special_tokens=True,
            )

            latex = (
                decoded[0]
                if decoded
                else None
            )

            return {
                "success": bool(latex),
                "latex": latex,
                "confidence": None,
                "error": None,
            }

        except Exception as exc:

            return {
                "success": False,
                "latex": None,
                "confidence": None,
                "error": str(exc),
            }

    return {
        "success": False,
        "latex": None,
        "confidence": None,
        "error": (
            "Не найден поддерживаемый "
            "API UniMERNet."
        ),
    }


def normalize_recognition_result(
    result: Any,
) -> Dict[str, Any]:
    """
    Приводит различные варианты ответа модели
    к единому диагностическому формату.
    """

    if result is None:

        return {
            "success": False,
            "latex": None,
            "confidence": None,
            "error": "Модель вернула None.",
        }

    if isinstance(
        result,
        str,
    ):

        return {
            "success": True,
            "latex": result,
            "confidence": None,
            "error": None,
        }

    if isinstance(
        result,
        dict,
    ):

        latex = (
            result.get("latex")
            or result.get("text")
            or result.get("prediction")
            or result.get("formula")
        )

        confidence = (
            result.get("confidence")
            or result.get("score")
        )

        return {
            "success": latex is not None,
            "latex": latex,
            "confidence": confidence,
            "error": result.get(
                "error"
            ),
        }

    return {
        "success": True,
        "latex": str(result),
        "confidence": None,
        "error": None,
    }


# ============================================================================
# GROUP DIAGNOSTICS
# ============================================================================


def print_header(
    semantic_file: Path,
    pages: Sequence[Dict[str, Any]],
) -> None:

    print(
        f"VKS Expert AI — "
        f"Formula Recognition Diagnostics "
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


def print_group(
    page: Dict[str, Any],
    group: Dict[str, Any],
) -> None:

    current_page = page_number(
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
        f"PAGE {current_page} / "
        f"GROUP {group_id}"
    )

    print(
        "=" * 80
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
        f"declared bbox    : "
        f"{fmt_bbox(group.get('bbox'))}"
    )

    print(
        f"members declared : "
        f"{len(group.get('parser_indices', []))}"
    )

    print(
        f"members resolved  : "
        f"{len(members)}"
    )

    print()
    print(
        "ELEMENTS"
    )

    print(
        "-" * 80
    )

    for position, element in enumerate(
        members,
        start=1,
    ):

        image_file = find_image_file(
            semantic_file,
            element,
        )

        print(
            f"    E{position}"
        )

        print(
            f"        parser_index : "
            f"{element.get('parser_index')}"
        )

        print(
            f"        source_index : "
            f"{element.get('source_index')}"
        )

        print(
            f"        xref         : "
            f"{element.get('xref')}"
        )

        print(
            f"        bbox         : "
            f"{fmt_bbox(element.get('bbox'))}"
        )

        if image_file:

            print(
                f"        image        : "
                f"{image_file}"
            )

        else:

            print(
                "        image        : NOT FOUND"
            )


# ============================================================================
# RECOGNITION OUTPUT
# ============================================================================


def print_recognition_result(
    position: int,
    element: Dict[str, Any],
    image_file: Optional[Path],
    result: Dict[str, Any],
) -> None:

    print()
    print(
        f"FORMULA #{position}"
    )

    print(
        "-" * 80
    )

    print(
        f"    parser_index : "
        f"{element.get('parser_index')}"
    )

    print(
        f"    xref         : "
        f"{element.get('xref')}"
    )

    print(
        f"    bbox         : "
        f"{fmt_bbox(element.get('bbox'))}"
    )

    print(
        f"    image        : "
        f"{image_file if image_file else 'NOT FOUND'}"
    )

    print(
        f"    success      : "
        f"{result.get('success')}"
    )

    confidence = result.get(
        "confidence"
    )

    print(
        f"    confidence   : "
        f"{confidence}"
    )

    print()

    print(
        "    LATEX"
    )

    print(
        "    -----"
    )

    latex = result.get(
        "latex"
    )

    if latex:

        print(
            f"    {latex}"
        )

    else:

        print(
            "    None"
        )

    error = result.get(
        "error"
    )

    if error:

        print()

        print(
            "    ERROR"
        )

        print(
            f"    {error}"
        )


# ============================================================================
# ARGUMENTS
# ============================================================================


def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description=(
            "VKS Expert AI — "
            "Formula Recognition Diagnostics"
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
            "Обработать composite groups."
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
        "--model-path",
        type=Path,
        default=None,
        help=(
            "Путь к локальной модели UniMERNet."
        ),
    )

    parser.add_argument(
        "--open",
        action="store_true",
        help=(
            "Открыть image crop перед распознаванием."
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

    print_header(
        semantic_file,
        pages,
    )

    print()
    print(
        "Loading UniMERNet..."
    )

    recognizer = load_unimernet(
        model_path=args.model_path
    )

    candidates = (
        get_unnumbered_composite_groups(
            data
        )
    )

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

    if args.all:

        selected = selected[
            : max(
                0,
                args.limit,
            )
        ]

    elif (
        args.page is None
        and args.group is None
    ):

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

        return

    total_formulas = 0
    successful_formulas = 0

    for (
        current_page,
        page,
        group,
    ) in selected:

        print_group(
            page,
            group,
        )

        members = resolve_group_members(
            page,
            group,
        )

        print()
        print(
            "RECOGNITION"
        )

        print(
            "-" * 80
        )

        for position, element in enumerate(
            members,
            start=1,
        ):

            total_formulas += 1

            image_file = find_image_file(
                semantic_file,
                element,
            )

            if image_file is None:

                result = {
                    "success": False,
                    "latex": None,
                    "confidence": None,
                    "error": (
                        "Image file "
                        "not found."
                    ),
                }

                print_recognition_result(
                    position,
                    element,
                    image_file,
                    result,
                )

                continue

            if args.open:

                open_file(
                    image_file
                )

            result = recognize_formula(
                recognizer,
                image_file,
            )

            if result.get(
                "success"
            ):

                successful_formulas += 1

            print_recognition_result(
                position,
                element,
                image_file,
                result,
            )

    print()
    print(
        "=" * 80
    )

    print(
        "SUMMARY"
    )

    print(
        "=" * 80
    )

    print(
        f"    groups processed : "
        f"{len(selected)}"
    )

    print(
        f"    formulas         : "
        f"{total_formulas}"
    )

    print(
        f"    successful       : "
        f"{successful_formulas}"
    )

    print(
        f"    failed           : "
        f"{total_formulas - successful_formulas}"
    )

    if total_formulas:

        success_ratio = (
            successful_formulas
            / total_formulas
        )

        print(
            f"    success ratio    : "
            f"{success_ratio:.3f}"
        )

    print()

    print(
        "NOTE:"
    )

    print(
        "    v0.1.0 is diagnostic only."
    )

    print(
        "    semantic JSON is not modified."
    )

    print(
        "    LaTeX is not yet converted to MathML."
    )

    print(
        "    No SP paragraph linking is performed."
    )


if __name__ == "__main__":
    main()
    