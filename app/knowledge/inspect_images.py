from pathlib import Path

import pymupdf


PDF_PATH = Path(
    r"knowledge\regulations\SP_30.13330\СП_30.13330_базовая_версия.pdf"
)

OUTPUT_DIR = Path(
    r"knowledge\diagnostics\page_12_images"
)

PAGE_NUMBER = 12


def main():
    document = pymupdf.open(PDF_PATH)

    source_page = document[PAGE_NUMBER - 1]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("VKS Expert AI — Image Map Diagnostic v0.3")
    print("=" * 70)

    print()
    print(f"Страница: {PAGE_NUMBER}")
    print(
        f"Размер: "
        f"{source_page.rect.width:.1f} × "
        f"{source_page.rect.height:.1f}"
    )

    images = source_page.get_images(full=True)

    unique_xrefs = []

    for image_info in images:
        xref = image_info[0]

        if xref not in unique_xrefs:
            unique_xrefs.append(xref)

    print()
    print(f"Изображений: {len(images)}")
    print(f"Уникальных xref: {len(unique_xrefs)}")

    # ---------------------------------------------------------
    # Создаём диагностический документ
    # ---------------------------------------------------------

    result = pymupdf.open()

    page = result.new_page(
        width=source_page.rect.width,
        height=source_page.rect.height,
    )

    # ---------------------------------------------------------
    # Копируем оригинальную страницу
    # ---------------------------------------------------------

    page.show_pdf_page(
        page.rect,
        document,
        PAGE_NUMBER - 1,
    )

    # ---------------------------------------------------------
    # Обводим изображения
    # ---------------------------------------------------------

    for xref in unique_xrefs:

        rects = source_page.get_image_rects(xref)

        for rect_index, rect in enumerate(rects):

            expanded = pymupdf.Rect(
                rect.x0 - 2,
                rect.y0 - 2,
                rect.x1 + 2,
                rect.y1 + 2,
            )

            # Красная рамка
            page.draw_rect(
                expanded,
                color=(1, 0, 0),
                width=1.5,
            )

            # Подпись
            label = f"xref={xref}"

            if len(rects) > 1:
                label += f"[{rect_index}]"

            label_rect = pymupdf.Rect(
                rect.x0,
                max(0, rect.y0 - 13),
                rect.x0 + 70,
                rect.y0,
            )

            page.draw_rect(
                label_rect,
                color=(1, 1, 0),
                fill=(1, 1, 0),
                width=0,
            )

            page.insert_textbox(
                label_rect,
                label,
                fontsize=5.5,
                fontname="helv",
                color=(0, 0, 0),
            )

    # ---------------------------------------------------------
    # Сохраняем
    # ---------------------------------------------------------

    output_pdf = (
        OUTPUT_DIR
        / "page_12_image_map.pdf"
    )

    result.save(
        output_pdf,
        garbage=4,
        deflate=True,
    )

    result.close()
    document.close()

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)

    print()
    print(
        f"Файл:"
    )
    print(output_pdf)


if __name__ == "__main__":
    main()
    