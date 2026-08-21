import pymupdf


PDF_PATH = r"knowledge\regulations\SP_30.13330\СП_30.13330_базовая_версия.pdf"


def main():
    document = pymupdf.open(PDF_PATH)

    print("=" * 60)
    print("VKS Expert AI — PDF diagnostic")
    print("=" * 60)

    print(f"Файл: {PDF_PATH}")
    print(f"Количество страниц: {len(document)}")

    for page_number, page in enumerate(document, start=1):
        text = page.get_text("text")

        print()
        print("-" * 60)
        print(f"СТРАНИЦА {page_number}")
        print("-" * 60)

        print(text[:1000])

        if page_number >= 3:
            break

    document.close()


if __name__ == "__main__":
    main()
    