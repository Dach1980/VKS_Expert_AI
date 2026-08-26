import fitz
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


PDF_PATH = (
    ROOT
    / "knowledge"
    / "regulations"
    / "SP_30.13330"
    / "СП_30.13330_базовая_версия.pdf"
)


OUTPUT_DIR = Path(
    r"D:\Projects\VKS_Expert_AI\knowledge\work\pages"
)


PAGE_NUMBER = 12


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    print("Opening PDF...")

    doc = fitz.open(PDF_PATH)


    print(
        "Pages:",
        len(doc)
    )


    page = doc[
        PAGE_NUMBER - 1
    ]


    print(
        "Page:",
        PAGE_NUMBER
    )


    print(
        "Size:",
        page.rect
    )


    pix = page.get_pixmap(
        dpi=200
    )


    output = OUTPUT_DIR / (
        f"SP30_page_{PAGE_NUMBER}.png"
    )


    pix.save(output)


    print(
        "Saved:",
        output
    )


    print(
        "Images:",
        len(page.get_images())
    )


    print(
        "Text length:",
        len(page.get_text())
    )


if __name__ == "__main__":
    main()
