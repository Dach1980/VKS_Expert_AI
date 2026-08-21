import json
from pathlib import Path
from statistics import median


# ============================================================
# CONFIG
# ============================================================

INPUT_PATH = Path(
    "knowledge/parsed/SP_30.13330.2020.elements.json"
)

OUTPUT_PATH = Path(
    "knowledge/parsed/SP_30.13330.2020.semantic.json"
)


# Пороговые значения.
#
# Они специально достаточно консервативные.
# На первом этапе мы не пытаемся "угадать" содержание
# изображения — только определить его роль.
#

SMALL_IMAGE_MAX_AREA = 1200

FORMULA_MIN_AREA = 1500

FORMULA_MAX_ASPECT_RATIO = 8.0

NEAR_DISTANCE = 35.0


# ============================================================
# GEOMETRY
# ============================================================

def bbox_width(bbox):
    return max(0.0, bbox[2] - bbox[0])


def bbox_height(bbox):
    return max(0.0, bbox[3] - bbox[1])


def bbox_area(bbox):
    return bbox_width(bbox) * bbox_height(bbox)


def bbox_center(bbox):
    return (
        (bbox[0] + bbox[2]) / 2,
        (bbox[1] + bbox[3]) / 2,
    )


def horizontal_distance(a, b):
    """
    Горизонтальное расстояние между двумя bbox.
    Если они пересекаются по X — расстояние 0.
    """

    if a[2] >= b[0] and b[2] >= a[0]:
        return 0.0

    if a[2] < b[0]:
        return b[0] - a[2]

    return a[0] - b[2]


def vertical_distance(a, b):
    """
    Вертикальное расстояние между двумя bbox.
    """

    if a[3] >= b[1] and b[3] >= a[1]:
        return 0.0

    if a[3] < b[1]:
        return b[1] - a[3]

    return a[1] - b[3]


def bbox_distance(a, b):
    """
    Упрощённое расстояние между bbox.
    """

    dx = horizontal_distance(a, b)
    dy = vertical_distance(a, b)

    return (dx ** 2 + dy ** 2) ** 0.5


# ============================================================
# IMAGE CLASSIFICATION
# ============================================================

def classify_image(element):
    """
    Первичная классификация изображения.

    ВАЖНО:
    Эта функция НЕ распознаёт содержание изображения.

    Она только определяет вероятную роль:
      - symbol
      - formula
      - unknown
    """

    bbox = element["bbox"]

    width = bbox_width(bbox)
    height = bbox_height(bbox)
    area = bbox_area(bbox)

    if height <= 0:
        return "unknown"

    aspect_ratio = width / height

    # Очень маленькие изображения.
    #
    # На нашей странице 12 сюда попадают отдельные
    # математические символы и буквы.
    if area <= SMALL_IMAGE_MAX_AREA:
        return "symbol"

    # Слишком вытянутые изображения пока не считаем
    # полноценными формулами автоматически.
    if aspect_ratio > FORMULA_MAX_ASPECT_RATIO:
        return "unknown"

    # Более крупные изображения.
    if area >= FORMULA_MIN_AREA:
        return "formula"

    return "unknown"


# ============================================================
# FORMULA NUMBER DETECTION
# ============================================================

def looks_like_formula_number(text):
    """
    Определяет текстовый элемент, который может содержать
    номер формулы:

        (1)
        (2)
        (3)

    и т.п.

    Это намеренно простое правило.
    """

    if not text:
        return False

    normalized = " ".join(text.split())

    if len(normalized) > 20:
        return False

    if normalized.startswith("(") and normalized.endswith(")"):
        inside = normalized[1:-1].strip()

        return inside.isdigit()

    return False


# ============================================================
# TEXT ROLE
# ============================================================

def classify_text(element):
    """
    Первичная классификация текстового блока.
    """

    text = element.get("text", "").strip()

    if not text:
        return "empty"

    if looks_like_formula_number(text):
        return "formula_number"

    return "text"


# ============================================================
# ELEMENT NORMALIZATION
# ============================================================

def normalize_element(element, index):
    """
    Приводит исходный элемент к единой структуре.
    """

    element_type = element.get("type")

    result = {
        "index": index,
        "type": element_type,
        "bbox": element.get("bbox"),
    }

    if element_type == "text":

        text = element.get("text", "")

        result["text"] = text
        result["role"] = classify_text(element)

    elif element_type == "image":

        result["xref"] = element.get("xref")
        result["role"] = classify_image(element)

        bbox = element["bbox"]

        result["width"] = round(
            bbox_width(bbox),
            2
        )

        result["height"] = round(
            bbox_height(bbox),
            2
        )

        result["area"] = round(
            bbox_area(bbox),
            2
        )

        if result["height"] > 0:
            result["aspect_ratio"] = round(
                result["width"] / result["height"],
                3
            )
        else:
            result["aspect_ratio"] = None

    return result


# ============================================================
# NEIGHBOURS
# ============================================================

def find_nearest_text(element, elements, direction=None):
    """
    Ищет ближайший текстовый элемент.

    direction:
        before — только элементы выше
        after  — только элементы ниже
        None   — любое направление
    """

    best = None
    best_distance = None

    bbox = element["bbox"]

    for candidate in elements:

        if candidate is element:
            continue

        if candidate["type"] != "text":
            continue

        candidate_bbox = candidate["bbox"]

        if direction == "before":
            if candidate_bbox[3] > bbox[1]:
                continue

        elif direction == "after":
            if candidate_bbox[1] < bbox[3]:
                continue

        distance = bbox_distance(
            bbox,
            candidate_bbox
        )

        if best_distance is None or distance < best_distance:
            best = candidate
            best_distance = distance

    if best is None:
        return None

    if best_distance is not None and best_distance > 180:
        return None

    return {
        "index": best["index"],
        "distance": round(best_distance, 2),
        "text": best.get("text", "").strip(),
        "role": best.get("role"),
    }


# ============================================================
# FORMULA CONTEXT
# ============================================================

def build_formula_context(elements):
    """
    Для каждой потенциальной формулы строит контекст.

    Например:

        text:
        "по формуле"

             ↓

        formula image

             ↓

        "(1)"
    """

    contexts = []

    for element in elements:

        if element["type"] != "image":
            continue

        if element["role"] != "formula":
            continue

        before = find_nearest_text(
            element,
            elements,
            direction="before"
        )

        after = find_nearest_text(
            element,
            elements,
            direction="after"
        )

        context = {
            "image_index": element["index"],
            "xref": element.get("xref"),
            "bbox": element["bbox"],
            "role": "formula",

            "before_text": before,
            "after_text": after,
        }

        contexts.append(context)

    return contexts


# ============================================================
# SYMBOL GROUPS
# ============================================================

def find_nearby_symbols(formula_element, elements):
    """
    Ищет маленькие изображения рядом с формулой.

    Это пока НЕ означает, что найденные изображения
    действительно являются переменными формулы.

    Мы только сохраняем геометрическую связь.
    """

    result = []

    formula_bbox = formula_element["bbox"]

    for element in elements:

        if element is formula_element:
            continue

        if element["type"] != "image":
            continue

        if element["role"] != "symbol":
            continue

        distance = bbox_distance(
            formula_bbox,
            element["bbox"]
        )

        if distance <= 120:
            result.append({
                "index": element["index"],
                "xref": element.get("xref"),
                "bbox": element["bbox"],
                "distance": round(distance, 2),
            })

    result.sort(
        key=lambda x: x["distance"]
    )

    return result


# ============================================================
# PAGE ANALYSIS
# ============================================================

def analyze_page(page, page_number):
    source_elements = page.get("elements", [])

    elements = []

    for index, element in enumerate(source_elements):
        normalized = normalize_element(
            element,
            index
        )

        elements.append(normalized)

    # --------------------------------------------------------
    # FORMULA CONTEXT
    # --------------------------------------------------------

    formula_contexts = build_formula_context(
        elements
    )

    # --------------------------------------------------------
    # SYMBOLS NEAR FORMULAS
    # --------------------------------------------------------

    formula_relations = []

    for element in elements:

        if element["type"] != "image":
            continue

        if element["role"] != "formula":
            continue

        nearby_symbols = find_nearby_symbols(
            element,
            elements
        )

        formula_relations.append({
            "formula_index": element["index"],
            "formula_xref": element.get("xref"),
            "nearby_symbols": nearby_symbols,
        })

    # --------------------------------------------------------
    # STATISTICS
    # --------------------------------------------------------

    text_count = sum(
        1
        for e in elements
        if e["type"] == "text"
    )

    image_count = sum(
        1
        for e in elements
        if e["type"] == "image"
    )

    symbol_count = sum(
        1
        for e in elements
        if e.get("role") == "symbol"
    )

    formula_count = sum(
        1
        for e in elements
        if e.get("role") == "formula"
    )

    formula_number_count = sum(
        1
        for e in elements
        if e.get("role") == "formula_number"
    )

    return {
        "page": page_number,

        "statistics": {
            "elements": len(elements),
            "text": text_count,
            "images": image_count,
            "symbols": symbol_count,
            "formula_candidates": formula_count,
            "formula_numbers": formula_number_count,
        },

        "elements": elements,

        "formula_contexts": formula_contexts,

        "formula_relations": formula_relations,
    }


# ============================================================
# DOCUMENT ANALYSIS
# ============================================================

def analyze_document(data):

    pages = data.get("pages", [])

    semantic_pages = []

    total_elements = 0
    total_images = 0
    total_symbols = 0
    total_formulas = 0
    total_formula_numbers = 0

    for page_index, page in enumerate(pages):

        page_number = page.get(
            "page",
            page_index + 1
        )

        print(
            f"Обработка страницы {page_number}..."
        )

        result = analyze_page(
            page,
            page_number
        )

        semantic_pages.append(result)

        statistics = result["statistics"]

        total_elements += statistics["elements"]
        total_images += statistics["images"]
        total_symbols += statistics["symbols"]
        total_formulas += statistics["formula_candidates"]
        total_formula_numbers += statistics[
            "formula_numbers"
        ]

    return {
        "schema_version": "0.2",

        "source": data.get(
            "source",
            "unknown"
        ),

        "statistics": {
            "pages": len(semantic_pages),
            "elements": total_elements,
            "images": total_images,
            "symbols": total_symbols,
            "formula_candidates": total_formulas,
            "formula_numbers": total_formula_numbers,
        },

        "pages": semantic_pages,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("VKS Expert AI — Semantic PDF Parser v0.2")
    print("=" * 60)

    print()
    print("Источник:")
    print(INPUT_PATH)

    print()
    print("Загрузка elements.json...")

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Файл не найден:\n{INPUT_PATH}"
        )

    with INPUT_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    print(
        f"Страниц: {len(data.get('pages', []))}"
    )

    print()
    print("Семантический анализ...")

    result = analyze_document(data)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("ГОТОВО")
    print("=" * 60)

    print()
    print("Результат:")
    print(OUTPUT_PATH)

    print()
    print("СТАТИСТИКА")
    print("-" * 60)

    stats = result["statistics"]

    print(
        f"Страниц:              {stats['pages']}"
    )

    print(
        f"Элементов:             {stats['elements']}"
    )

    print(
        f"Изображений:           {stats['images']}"
    )

    print(
        f"Символов:              {stats['symbols']}"
    )

    print(
        f"Кандидатов формул:     {stats['formula_candidates']}"
    )

    print(
        f"Номеров формул:        {stats['formula_numbers']}"
    )


if __name__ == "__main__":
    main()
    