import json
import re
from pathlib import Path

import pymupdf


PDF_PATH = Path(
    r"knowledge\regulations\SP_30.13330\СП_30.13330_базовая_версия.pdf"
)

OUTPUT_PATH = Path(
    r"knowledge\parsed\SP_30.13330.2020.json"
)


# ---------------------------------------------------------
# Определение номера нормативного пункта
# ---------------------------------------------------------

CLAUSE_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+){0,5})\s+(.+)"
)


def detect_clause(line: str):
    """
    Определяет, является ли строка началом нормативного пункта.

    Примеры:

    1 Область применения
    1.1 Настоящий свод правил...
    7.2.1 В зданиях...
    """

    match = CLAUSE_PATTERN.match(line)

    if not match:
        return None

    number = match.group(1)
    text = match.group(2).strip()

    return {
        "number": number,
        "text": text,
    }


# ---------------------------------------------------------
# Извлечение страницы
# ---------------------------------------------------------

def extract_page(page, page_number: int):
    """
    Извлекает текстовые блоки страницы.

    Для каждого блока сохраняются:
    - текст
    - координаты
    - номер страницы
    """

    blocks = page.get_text("blocks")

    result = []

    for block in blocks:
        x0, y0, x1, y1, text, *_ = block

        text = text.strip()

        if not text:
            continue

        result.append(
            {
                "page": page_number,
                "bbox": [
                    round(x0, 2),
                    round(y0, 2),
                    round(x1, 2),
                    round(y1, 2),
                ],
                "text": text,
            }
        )

    return result


# ---------------------------------------------------------
# Основной parser
# ---------------------------------------------------------

def parse_pdf(pdf_path: Path):
    document = pymupdf.open(pdf_path)

    pages = []
    clauses = []

    current_clause = None

    for page_number, page in enumerate(document, start=1):

        blocks = extract_page(page, page_number)

        pages.append(
            {
                "page": page_number,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "blocks": blocks,
            }
        )

        for block in blocks:

            lines = block["text"].splitlines()

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                detected = detect_clause(line)

                if detected:

                    if current_clause:
                        clauses.append(current_clause)

                    current_clause = {
                        "number": detected["number"],
                        "text": detected["text"],
                        "page_start": page_number,
                        "page_end": page_number,
                        "bbox": block["bbox"],
                    }

                elif current_clause:

                    current_clause["text"] += " " + line
                    current_clause["page_end"] = page_number

    if current_clause:
        clauses.append(current_clause)

    document.close()

    return {
        "document": {
            "number": "СП 30.13330.2020",
            "title": "Внутренний водопровод и канализация зданий",
            "source_file": pdf_path.name,
            "pages": len(pages),
        },
        "pages": pages,
        "clauses": clauses,
    }


# ---------------------------------------------------------
# Сохранение JSON
# ---------------------------------------------------------

def save_json(data, output_path: Path):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ---------------------------------------------------------
# Запуск
# ---------------------------------------------------------

def main():

    print("=" * 60)
    print("VKS Expert AI — PDF Parser v0.1")
    print("=" * 60)

    print()
    print(f"Источник:")
    print(PDF_PATH)

    print()
    print("Обработка PDF...")

    data = parse_pdf(PDF_PATH)

    save_json(
        data,
        OUTPUT_PATH,
    )

    print()
    print("Готово.")

    print()
    print(f"Страниц: {len(data['pages'])}")
    print(f"Найдено пунктов: {len(data['clauses'])}")

    print()
    print("Результат:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
    