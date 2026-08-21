import json
from pathlib import Path

import pymupdf


# ============================================================
# CONFIG
# ============================================================

PDF_PATH = Path(
    r"knowledge\regulations\SP_30.13330\СП_30.13330_базовая_версия.pdf"
)

OUTPUT_PATH = Path(
    r"knowledge\parsed\SP_30.13330.2020.elements.json"
)

IMAGE_DIR = Path(
    r"knowledge\parsed\SP_30.13330.2020.images"
)


# ============================================================
# TEXT ELEMENT
# ============================================================

def extract_text_elements(page, page_number):
    """
    Извлекает текстовые блоки страницы.

    Каждый блок становится отдельным элементом.
    """

    elements = []

    blocks = page.get_text("blocks")

    for block in blocks:

        x0, y0, x1, y1, text, *_ = block

        text = text.strip()

        if not text:
            continue

        elements.append(
            {
                "type": "text",
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

    return elements


# ============================================================
# IMAGE ELEMENTS
# ============================================================
def extract_image_elements(page, page_number, document):
    """
    Извлекает изображения страницы.

    Каждый xref обрабатывается только один раз.

    Если одно и то же изображение используется
    несколько раз на странице, для него создаётся
    отдельный element с соответствующим bbox.
    """

    elements = []

    images = page.get_images(full=True)

    # -----------------------------------------------------
    # Защита от повторного xref
    # -----------------------------------------------------

    processed_xrefs = set()

    for image in images:

        xref = image[0]

        if xref in processed_xrefs:
            continue

        processed_xrefs.add(xref)

        # -------------------------------------------------
        # Получаем все места использования изображения
        # -------------------------------------------------

        rects = page.get_image_rects(xref)

        if not rects:
            continue

        # -------------------------------------------------
        # Извлекаем изображение
        # -------------------------------------------------

        image_info = document.extract_image(xref)

        image_bytes = image_info["image"]
        image_ext = image_info["ext"]

        image_path = (
            IMAGE_DIR
            / f"image_xref_{xref}.{image_ext}"
        )

        if not image_path.exists():

            image_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with image_path.open("wb") as file:
                file.write(image_bytes)

        # -------------------------------------------------
        # Создаём element для каждого использования
        # -------------------------------------------------

        for rect in rects:

            elements.append(
                {
                    "type": "image",
                    "page": page_number,
                    "xref": xref,
                    "bbox": [
                        round(rect.x0, 2),
                        round(rect.y0, 2),
                        round(rect.x1, 2),
                        round(rect.y1, 2),
                    ],
                    "width": image_info["width"],
                    "height": image_info["height"],
                    "format": image_ext,
                    "file": str(image_path),
                }
            )

    return elements

# ============================================================
# SORTING
# ============================================================

def sort_elements(elements):
    """
    Сортирует элементы в порядке их расположения
    на странице.

    Основной порядок:
    1. Y
    2. X
    """

    return sorted(
        elements,
        key=lambda element: (
            element["bbox"][1],
            element["bbox"][0],
        ),
    )


# ============================================================
# PAGE PARSER
# ============================================================

def parse_page(page, page_number, document):

    text_elements = extract_text_elements(
        page,
        page_number,
    )

    image_elements = extract_image_elements(
        page,
        page_number,
        document,
    )

    elements = (
        text_elements
        + image_elements
    )

    elements = sort_elements(elements)

    return {
        "page": page_number,
        "width": round(page.rect.width, 2),
        "height": round(page.rect.height, 2),
        "elements": elements,
    }


# ============================================================
# PDF PARSER
# ============================================================

def parse_pdf(pdf_path):

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        document,
        start=1,
    ):

        page_data = parse_page(
            page,
            page_number,
            document,
        )

        pages.append(page_data)

    document.close()

    return {
        "document": {
            "number": "СП 30.13330.2020",
            "title": (
                "Внутренний водопровод "
                "и канализация зданий"
            ),
            "source_file": pdf_path.name,
            "pages": len(pages),
        },
        "pages": pages,
    }


# ============================================================
# SAVE
# ============================================================

def save_json(data, output_path):

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


# ============================================================
# DIAGNOSTICS
# ============================================================

def print_statistics(data):

    pages = data["pages"]

    text_count = 0
    image_count = 0

    for page in pages:

        for element in page["elements"]:

            if element["type"] == "text":
                text_count += 1

            elif element["type"] == "image":
                image_count += 1

    print()
    print("СТАТИСТИКА")
    print("-" * 60)
    print(f"Страниц:          {len(pages)}")
    print(f"Текстовых блоков: {text_count}")
    print(f"Изображений:      {image_count}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("VKS Expert AI — PDF Element Parser v0.1")
    print("=" * 70)

    print()
    print("Источник:")
    print(PDF_PATH)

    print()
    print("Обработка PDF...")

    data = parse_pdf(PDF_PATH)

    save_json(
        data,
        OUTPUT_PATH,
    )

    print_statistics(data)

    print()
    print("Результат:")
    print(OUTPUT_PATH)

    print()
    print("Изображения:")
    print(IMAGE_DIR)


if __name__ == "__main__":
    main()
