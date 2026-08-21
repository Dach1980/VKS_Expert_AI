import pymupdf
from pathlib import Path


PDF_PATH = Path(
    r"knowledge\regulations\SP_30.13330\СП_30.13330_базовая_версия.pdf"
)

OUTPUT_DIR = Path(
    r"knowledge\diagnostics\page_12_images"
)


def main():

    print("=" * 70)
    print("VKS Expert AI — PDF image diagnostic v0.3")
    print("=" * 70)

    print()
    print(f"PDF:")
    print(PDF_PATH)

    if not PDF_PATH.exists():
        print()
        print("ОШИБКА: PDF не найден.")
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    document = pymupdf.open(PDF_PATH)

    page_number = 12
    page = document[page_number - 1]

    print()
    print(f"Страница: {page_number}")
    print(f"Размер страницы: {page.rect.width:.1f} × {page.rect.height:.1f}")

    images = page.get_images(full=True)

    print()
    print(f"Найдено изображений: {len(images)}")

    print()
    print("-" * 70)

    saved = set()

    for index, image in enumerate(images):

        xref = image[0]

        width = image[2]
        height = image[3]

        print()
        print(f"[IMAGE {index}]")
        print(f"  xref:   {xref}")
        print(f"  size:   {width} × {height}")

        rects = page.get_image_rects(xref)

        for rect_index, rect in enumerate(rects):

            print(
                f"  rect {rect_index}: "
                f"({rect.x0:.1f}, {rect.y0:.1f}) - "
                f"({rect.x1:.1f}, {rect.y1:.1f})"
            )

        # -----------------------------------------------------
        # Один и тот же xref может использоваться несколько раз
        # -----------------------------------------------------

        if xref in saved:
            print("  Файл уже сохранён ранее.")
            continue

        try:

            image_data = document.extract_image(xref)

            extension = image_data["ext"]

            output_file = (
                OUTPUT_DIR
                / f"image_{index:02d}_xref_{xref}.{extension}"
            )

            with output_file.open("wb") as file:
                file.write(image_data["image"])

            saved.add(xref)

            print(
                f"  Сохранено: {output_file}"
            )

        except Exception as error:

            print(
                f"  ОШИБКА извлечения: {error}"
            )

    document.close()

    print()
    print("=" * 70)
    print("ГОТОВО")
    print("=" * 70)

    print()
    print(f"Изображения сохранены в:")
    print(OUTPUT_DIR)

    print()
    print(f"Уникальных изображений: {len(saved)}")


if __name__ == "__main__":
    main()
    