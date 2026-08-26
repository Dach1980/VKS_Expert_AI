from pathlib import Path
import pymupdf


ROOT = Path(__file__).resolve().parents[2]

PDF_PATH = (
    ROOT
    / "knowledge"
    / "regulations"
    / "SP_30.13330"
    / "СП_30.13330_базовая_версия.pdf"
)

PAGE_NUMBER = 12


def main():

    print("Opening PDF...")

    doc = pymupdf.open(PDF_PATH)

    print("Pages:", len(doc))

    page = doc[PAGE_NUMBER - 1]

    print()
    print("=" * 80)
    print(f"PAGE {PAGE_NUMBER}")
    print("=" * 80)

    print()
    print("PAGE SIZE:")
    print(page.rect)

    # ---------------------------------------------------------
    # TEXT
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("TEXT BLOCKS")
    print("=" * 80)

    blocks = page.get_text("blocks")

    print("Total blocks:", len(blocks))

    for index, block in enumerate(blocks):

        x0, y0, x1, y1, text, block_no, block_type = block[:7]

        print()
        print(f"BLOCK {index}")
        print("-" * 60)

        print(
            f"BBOX: "
            f"x0={x0:.1f}, "
            f"y0={y0:.1f}, "
            f"x1={x1:.1f}, "
            f"y1={y1:.1f}"
        )

        print("TYPE:", block_type)

        print("TEXT:")
        print(repr(text[:500]))

    # ---------------------------------------------------------
    # IMAGES
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("IMAGES")
    print("=" * 80)

    images = page.get_images(full=True)

    print("Total images:", len(images))

    for index, image in enumerate(images):

        xref = image[0]

        print()
        print(f"IMAGE {index}")
        print("-" * 60)

        print("XREF:", xref)

        try:
            rects = page.get_image_rects(xref)

            print("RECTS:", rects)

        except Exception as e:

            print("RECT ERROR:", e)

    # ---------------------------------------------------------
    # DRAWINGS
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("DRAWINGS")
    print("=" * 80)

    drawings = page.get_drawings()

    print("Total drawings:", len(drawings))

    for index, drawing in enumerate(drawings[:100]):

        print()
        print(f"DRAWING {index}")
        print("-" * 60)

        print("RECT:", drawing.get("rect"))

        print("TYPE:", drawing.get("type"))

        print("ITEMS:", len(drawing.get("items", [])))

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
    