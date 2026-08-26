
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pymupdf


# -----------------------------------------------------------------------------
# Project paths
# -----------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PDF = (
    PROJECT_ROOT
    / "knowledge"
    / "regulations"
    / "SP_30.13330"
    / "СП_30.13330_базовая_версия.pdf"
)

DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT
    / "knowledge"
    / "work"
    / "formulas"
)


# -----------------------------------------------------------------------------
# FormulaRecognizer import
# -----------------------------------------------------------------------------

try:
    from vision.formula_recognizer import FormulaRecognizer
except ModuleNotFoundError:
    # When the script is launched directly from app/knowledge/,
    # the project root may not be in sys.path.
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from vision.formula_recognizer import FormulaRecognizer


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Objects smaller than these values are usually individual mathematical
# symbols or tiny PDF fragments rather than a complete formula.
MIN_WIDTH = 25.0
MIN_HEIGHT = 12.0

# Minimum area.
MIN_AREA = 400.0

# Padding around detected object when rendering the crop.
CROP_PADDING = 8.0

# Render scale.
# 2.0 gives substantially more pixels to UniMERNet than the native PDF size.
RENDER_SCALE = 2.0

# Duplicate rectangles tolerance.
RECT_TOLERANCE = 1.0


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def rect_to_list(rect: pymupdf.Rect) -> list[float]:
    return [
        round(rect.x0, 3),
        round(rect.y0, 3),
        round(rect.x1, 3),
        round(rect.y1, 3),
    ]


def normalize_latex(value: str) -> str:
    """
    Normalize UniMERNet output without changing mathematical content.
    """
    if not value:
        return ""

    value = value.strip()

    # Collapse repeated whitespace.
    value = " ".join(value.split())

    return value


def rect_almost_equal(
    a: pymupdf.Rect,
    b: pymupdf.Rect,
    tolerance: float = RECT_TOLERANCE,
) -> bool:
    return (
        abs(a.x0 - b.x0) <= tolerance
        and abs(a.y0 - b.y0) <= tolerance
        and abs(a.x1 - b.x1) <= tolerance
        and abs(a.y1 - b.y1) <= tolerance
    )


def rect_area(rect: pymupdf.Rect) -> float:
    return max(0.0, rect.width) * max(0.0, rect.height)


def rect_center(rect: pymupdf.Rect) -> tuple[float, float]:
    return (
        (rect.x0 + rect.x1) / 2.0,
        (rect.y0 + rect.y1) / 2.0,
    )


def distance_between_rects(
    a: pymupdf.Rect,
    b: pymupdf.Rect,
) -> float:
    """
    Euclidean distance between two rectangles.
    Returns 0 when they intersect.
    """

    if a.intersects(b):
        return 0.0

    ax, ay = rect_center(a)
    bx, by = rect_center(b)

    return math.sqrt(
        (ax - bx) ** 2
        + (ay - by) ** 2
    )


# -----------------------------------------------------------------------------
# Text extraction
# -----------------------------------------------------------------------------

def get_text_blocks(page: pymupdf.Page) -> list[dict[str, Any]]:
    """
    Extract text blocks together with their PDF coordinates.
    """

    blocks = []

    raw_blocks = page.get_text("blocks")

    for index, block in enumerate(raw_blocks):

        if len(block) < 5:
            continue

        x0, y0, x1, y1, text = block[:5]

        text = text.strip()

        if not text:
            continue

        blocks.append(
            {
                "index": index,
                "bbox": [
                    round(x0, 3),
                    round(y0, 3),
                    round(x1, 3),
                    round(y1, 3),
                ],
                "text": text,
            }
        )

    return blocks


# -----------------------------------------------------------------------------
# Image / formula candidate detection
# -----------------------------------------------------------------------------

def get_image_candidates(
    page: pymupdf.Page,
) -> list[dict[str, Any]]:
    """
    Find raster image rectangles on the page.

    Important:
    We use get_image_rects() rather than simply extracting image bytes.

    This preserves the actual position of the object on the PDF page.
    """

    candidates = []

    seen_rects: list[pymupdf.Rect] = []

    images = page.get_images(full=True)

    for image_index, image_info in enumerate(images):

        xref = image_info[0]

        try:
            rects = page.get_image_rects(xref)
        except Exception:
            continue

        for rect_index, rect in enumerate(rects):

            if rect.width <= 0 or rect.height <= 0:
                continue

            width = rect.width
            height = rect.height
            area = rect_area(rect)

            # Filter tiny image fragments.
            if width < MIN_WIDTH:
                continue

            if height < MIN_HEIGHT:
                continue

            if area < MIN_AREA:
                continue

            # Remove duplicate placements.
            duplicate = any(
                rect_almost_equal(rect, existing)
                for existing in seen_rects
            )

            if duplicate:
                continue

            seen_rects.append(rect)

            candidates.append(
                {
                    "image_index": image_index,
                    "rect_index": rect_index,
                    "xref": xref,
                    "bbox": rect_to_list(rect),
                    "width": round(width, 3),
                    "height": round(height, 3),
                    "area": round(area, 3),
                }
            )

    # Sort top-to-bottom, left-to-right.
    candidates.sort(
        key=lambda item: (
            item["bbox"][1],
            item["bbox"][0],
        )
    )

    return candidates


# -----------------------------------------------------------------------------
# Context matching
# -----------------------------------------------------------------------------

def find_nearest_text_block(
    formula_rect: pymupdf.Rect,
    text_blocks: list[dict[str, Any]],
) -> dict[str, Any] | None:

    if not text_blocks:
        return None

    best = None
    best_score = float("inf")

    fx = (formula_rect.x0 + formula_rect.x1) / 2.0
    fy = formula_rect.y0

    for block in text_blocks:

        bx0, by0, bx1, by1 = block["bbox"]

        # Prefer text located above the formula.
        if by1 <= formula_rect.y0 + 5:

            vertical_distance = max(
                0.0,
                formula_rect.y0 - by1,
            )

            horizontal_distance = abs(
                fx - ((bx0 + bx1) / 2.0)
            )

            score = (
                vertical_distance * 2.0
                + horizontal_distance * 0.2
            )

        else:
            # Text below / beside the formula gets a penalty.
            distance = distance_between_rects(
                formula_rect,
                pymupdf.Rect(*block["bbox"]),
            )

            score = distance + 100.0

        if score < best_score:
            best_score = score
            best = block

    return best


# -----------------------------------------------------------------------------
# Crop rendering
# -----------------------------------------------------------------------------

def render_formula_crop(
    page: pymupdf.Page,
    rect: pymupdf.Rect,
    output_path: Path,
) -> None:

    page_rect = page.rect

    crop = pymupdf.Rect(
        rect.x0 - CROP_PADDING,
        rect.y0 - CROP_PADDING,
        rect.x1 + CROP_PADDING,
        rect.y1 + CROP_PADDING,
    )

    crop &= page_rect

    matrix = pymupdf.Matrix(
        RENDER_SCALE,
        RENDER_SCALE,
    )

    pixmap = page.get_pixmap(
        matrix=matrix,
        clip=crop,
        alpha=False,
    )

    pixmap.save(str(output_path))


# -----------------------------------------------------------------------------
# FormulaRecognizer adapter
# -----------------------------------------------------------------------------

def recognize_formula(
    recognizer: FormulaRecognizer,
    image_path: Path,
) -> dict[str, Any]:

    result = recognizer.recognize(str(image_path))

    if isinstance(result, str):
        return {
            "latex": normalize_latex(result),
            "raw": result,
        }

    if not isinstance(result, dict):
        return {
            "latex": "",
            "raw": str(result),
        }

    latex = result.get("latex", "")

    raw = result.get(
        "raw",
        result.get("pred_str", ""),
    )

    tokens = result.get("tokens")

    return {
        "latex": normalize_latex(str(latex)),
        "raw": normalize_latex(str(raw)),
        "tokens": tokens,
    }


# -----------------------------------------------------------------------------
# Main page processing
# -----------------------------------------------------------------------------

def process_page(
    pdf_path: Path,
    page_number: int,
    output_dir: Path,
    recognizer: FormulaRecognizer,
) -> dict[str, Any]:

    print()
    print("=" * 80)
    print(f"Processing page {page_number}")
    print("=" * 80)

    doc = pymupdf.open(str(pdf_path))

    try:

        if page_number < 1 or page_number > len(doc):
            raise ValueError(
                f"Page {page_number} is outside PDF range 1..{len(doc)}"
            )

        page = doc[page_number - 1]

        page_dir = output_dir / f"page_{page_number:03d}"
        page_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        text_blocks = get_text_blocks(page)

        candidates = get_image_candidates(page)

        print(f"Page size: {page.rect}")
        print(f"Text blocks: {len(text_blocks)}")
        print(f"Formula candidates: {len(candidates)}")

        formulas = []

        for formula_index, candidate in enumerate(candidates, start=1):

            rect = pymupdf.Rect(
                *candidate["bbox"]
            )

            crop_path = (
                page_dir
                / f"formula_{formula_index:03d}.png"
            )

            print()
            print(
                f"[{formula_index}] "
                f"bbox={candidate['bbox']} "
                f"size={candidate['width']:.1f}x"
                f"{candidate['height']:.1f}"
            )

            render_formula_crop(
                page=page,
                rect=rect,
                output_path=crop_path,
            )

            print(
                f"  crop: {crop_path}"
            )

            context_block = find_nearest_text_block(
                formula_rect=rect,
                text_blocks=text_blocks,
            )

            if context_block:
                print(
                    "  context:",
                    context_block["text"].replace("\n", " "),
                )

            try:

                recognition = recognize_formula(
                    recognizer=recognizer,
                    image_path=crop_path,
                )

                latex = recognition.get(
                    "latex",
                    "",
                )

                print(
                    "  LaTeX:",
                    latex if latex else "<empty>",
                )

            except Exception as exc:

                print(
                    "  recognition ERROR:",
                    repr(exc),
                )

                recognition = {
                    "latex": "",
                    "raw": "",
                    "error": str(exc),
                }

            formula_record = {
                "id": (
                    f"sp30-page-{page_number:03d}"
                    f"-formula-{formula_index:03d}"
                ),
                "page": page_number,
                "type": "formula",

                "bbox": candidate["bbox"],

                "pdf_coordinates": {
                    "x0": candidate["bbox"][0],
                    "y0": candidate["bbox"][1],
                    "x1": candidate["bbox"][2],
                    "y1": candidate["bbox"][3],
                },

                "source": {
                    "pdf": str(pdf_path),
                    "page": page_number,
                    "xref": candidate["xref"],
                    "image_index": candidate["image_index"],
                    "rect_index": candidate["rect_index"],
                },

                "crop": {
                    "path": str(crop_path),
                    "padding": CROP_PADDING,
                    "render_scale": RENDER_SCALE,
                },

                "recognition": recognition,

                "context": {
                    "nearest_text_block": context_block,
                },
            }

            formulas.append(formula_record)

        result = {
            "document": {
                "name": pdf_path.name,
                "path": str(pdf_path),
            },

            "page": {
                "number": page_number,
                "width": round(page.rect.width, 3),
                "height": round(page.rect.height, 3),
            },

            "text_blocks_count": len(text_blocks),

            "formula_candidates_count": len(candidates),

            "formulas": formulas,
        }

        json_path = (
            page_dir
            / f"page_{page_number:03d}_formulas.json"
        )

        with json_path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                result,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print()
        print("=" * 80)
        print(f"JSON saved: {json_path}")
        print("=" * 80)

        return result

    finally:
        doc.close()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Extract formula candidates from a PDF page, "
            "recognize them with UniMERNet and save coordinates + LaTeX to JSON."
        )
    )

    parser.add_argument(
        "--pdf",
        default=str(DEFAULT_PDF),
        help="Path to PDF",
    )

    parser.add_argument(
        "--page",
        type=int,
        default=12,
        help="Page number, 1-based",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory",
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    print("Loading FormulaRecognizer...")

    recognizer = FormulaRecognizer()

    print("FormulaRecognizer loaded")

    process_page(
        pdf_path=pdf_path,
        page_number=args.page,
        output_dir=output_dir,
        recognizer=recognizer,
    )


if __name__ == "__main__":
    main()

