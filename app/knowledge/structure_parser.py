import json
import re
from pathlib import Path
from text_cleaner import clean_clause_text


# ============================================================
# VKS Expert AI — Structure Parser v0.4
# ============================================================

INPUT_PATH = Path(
    "knowledge/parsed/SP_30.13330.2020.json"
)

OUTPUT_PATH = Path(
    "knowledge/structured/SP_30.13330.2020.json"
)


DOCUMENT_NUMBER = "СП 30.13330.2020"
DOCUMENT_TITLE = "Внутренний водопровод и канализация зданий"


# ============================================================
# ОЖИДАЕМЫЕ РАЗДЕЛЫ СП 30.13330.2020
# ============================================================

EXPECTED_SECTIONS = {
    1: "Область применения",
    2: "Нормативные ссылки",
    3: "Термины, определения, обозначения и единицы измерения",
    4: "Общие положения",
    5: "Определение расчетных расходов воды, стоков и тепла на приготовление горячей воды",
    6: "Системы холодного водоснабжения",
    7: "Противопожарный водопровод",
    8: "Устройство систем холодного водоснабжения",
    9: "Системы горячего водоснабжения",
    10: "Устройство систем горячего водоснабжения",
    11: "Трубопроводы и арматура",
    12: "Устройства для измерения расхода воды",
    13: "Насосные установки",
    14: "Запасные и регулирующие емкости",
    15: "Дополнительные требования к системам внутреннего водоснабжения в особых условиях",
    16: "Системы водоотведения",
    17: "Санитарно-технические приборы и приемники сточных вод",
    18: "Устройство систем водоотведения",
    19: "Расчет внутренней системы водоотведения",
    20: "Местные установки для очистки и перекачки сточных вод",
    21: "Внутренние водостоки",
    22: "Дополнительные требования к внутренним системам водоотведения и водостокам в особых условиях",
    23: "Санитарно-эпидемиологические и гигиенические требования, требования охраны",
    24: "Обеспечение надежности и безопасности при эксплуатации. Долговечность и",
    25: "Порядок проведения монтажа и сдачи в эксплуатацию внутренних систем",
    26: "Требования энергетической эффективности внутренних систем водоснабжения и",
}


# ============================================================
# REGEX
# ============================================================

SECTION_PATTERN = re.compile(
    r"^(\d{1,2})\s+(.+)$"
)


CLAUSE_PATTERN = re.compile(
    r"^(\d+(?:\.\d+)+)\s+(.+)$"
)


APPENDIX_PATTERN = re.compile(
    r"^Приложение\s+([А-ЯЁA-Z])(?:\s+(.*))?$",
    re.IGNORECASE
)


# ============================================================
# STATES
# ============================================================

STATE_PREAMBLE = "preamble"
STATE_MAIN = "main"
STATE_APPENDIX = "appendix"


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(text: str) -> str:
    """
    Нормализация текста, полученного из PDF.
    """

    if not text:
        return ""

    text = text.replace("\u00ad", "")
    text = text.replace("\xa0", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# DETECTION
# ============================================================

def detect_section(text: str):
    """
    Распознаёт потенциальный заголовок раздела.
    """

    match = SECTION_PATTERN.match(text)

    if not match:
        return None

    number = int(match.group(1))
    title = match.group(2).strip()

    return {
        "number": number,
        "title": title,
    }


def detect_clause(text: str):
    """
    Распознаёт нормативный пункт:

        5.1
        5.2
        18.19
        18.26
    """

    match = CLAUSE_PATTERN.match(text)

    if not match:
        return None

    number = match.group(1)
    content = match.group(2).strip()

    return {
        "number": number,
        "text": content,
        "level": number.count(".") + 1,
    }


def detect_appendix(text: str):
    """
    Распознаёт:

        Приложение А
        Приложение Б
        ...
    """

    match = APPENDIX_PATTERN.match(text)

    if not match:
        return None

    number = match.group(1)
    title = (match.group(2) or "").strip()

    return {
        "number": number,
        "title": title,
    }


# ============================================================
# SECTION VALIDATION
# ============================================================

def is_real_section(section):
    """
    Проверяет, является ли потенциальный заголовок
    настоящим разделом СП.

    Для СП 30.13330.2020 допустимы только разделы 1–26.

    Дополнительно проверяем название.
    """

    if not section:
        return False

    number = section["number"]

    if number not in EXPECTED_SECTIONS:
        return False

    detected_title = normalize_text(
        section["title"]
    ).lower()

    expected_title = normalize_text(
        EXPECTED_SECTIONS[number]
    ).lower()

    # Первое слово/начало названия должно совпадать.
    #
    # Это позволяет пережить обрезанный PDF-заголовок.
    if detected_title.startswith(
        expected_title[:20]
    ):
        return True

    # Для некоторых заголовков PDF может
    # обрезать конец строки.
    #
    # Проверяем наличие нескольких ключевых слов.

    important_words = [
        word
        for word in re.findall(
            r"[а-яёa-z]+",
            expected_title
        )
        if len(word) >= 5
    ]

    if not important_words:
        return False

    matches = sum(
        1
        for word in important_words
        if word in detected_title
    )

    return matches >= min(
        3,
        len(important_words)
    )


# ============================================================
# CLAUSE ADD
# ============================================================

def add_block_to_clause(
    clause,
    block,
    page_number,
    text=None
):
    """
    Добавляет продолжение текста пункта.
    """

    if text is None:
        text = block.get("text", "")

    text = normalize_text(text)

    if not text:
        return

    if clause["text"]:
        clause["text"] += " " + text
    else:
        clause["text"] = text

    clause["page_end"] = page_number

    clause["source"]["blocks"].append(
        {
            "page": page_number,
            "bbox": block.get("bbox"),
        }
    )


# ============================================================
# BUILD STRUCTURE
# ============================================================

def build_structure(data):

    document = data["document"]

    sections = []

    current_section = None
    current_clause = None

    state = STATE_PREAMBLE

    found_sections = set()

    # --------------------------------------------------------
    # Проходим страницы
    # --------------------------------------------------------

    for page in data["pages"]:

        page_number = page["page"]

        for block in page["blocks"]:

            raw_text = block.get(
                "text",
                ""
            )

            if not raw_text:
                continue

            lines = raw_text.splitlines()

            for raw_line in lines:

                line = normalize_text(
                    raw_line
                )

                if not line:
                    continue

                # ====================================================
                # APPENDIX
                # ====================================================

                appendix = detect_appendix(
                    line
                )

                if appendix:

                    state = STATE_APPENDIX

                    current_clause = None

                    appendix_data = {
                        "type": "appendix",
                        "number": appendix["number"],
                        "title": appendix["title"],
                        "page_start": page_number,
                        "page_end": page_number,
                        "blocks": [],
                    }

                    sections.append(
                        appendix_data
                    )

                    current_section = (
                        appendix_data
                    )

                    continue

                # ====================================================
                # POTENTIAL SECTION
                # ====================================================

                section = detect_section(
                    line
                )

                if section:

                    number = section["number"]

                    # ------------------------------------------------
                    # Ищем первый настоящий раздел
                    # ------------------------------------------------

                    if state == STATE_PREAMBLE:

                        if (
                            number == 1
                            and is_real_section(
                                section
                            )
                        ):

                            state = STATE_MAIN

                        else:
                            continue

                    # ------------------------------------------------
                    # Основная часть документа
                    # ------------------------------------------------

                    if state == STATE_MAIN:

                        if (
                            is_real_section(
                                section
                            )
                            and number
                            not in found_sections
                        ):

                            current_section = {
                                "type": "section",
                                "number": number,
                                "title": section[
                                    "title"
                                ],
                                "page_start": page_number,
                                "page_end": page_number,
                                "clauses": [],
                            }

                            sections.append(
                                current_section
                            )

                            found_sections.add(
                                number
                            )

                            current_clause = None

                            continue

                # ====================================================
                # CLAUSE
                # ====================================================

                clause = detect_clause(
                    line
                )

                if (
                    clause
                    and state == STATE_MAIN
                    and current_section
                    and current_section.get(
                        "type"
                    ) == "section"
                ):

                    section_number = (
                        current_section[
                            "number"
                        ]
                    )

                    prefix = (
                        str(section_number)
                        + "."
                    )

                    if clause[
                        "number"
                    ].startswith(prefix):

                        current_clause = {
                            "type": "clause",
                            "number": clause[
                                "number"
                            ],
                            "level": clause[
                                "level"
                            ],
                            "text": clause[
                                "text"
                            ],
                            "page_start": page_number,
                            "page_end": page_number,
                            "source": {
                                "file": document.get(
                                    "source_file"
                                ),
                                "blocks": [
                                    {
                                        "page": page_number,
                                        "bbox": block.get(
                                            "bbox"
                                        ),
                                    }
                                ],
                            },
                        }

                        current_section[
                            "clauses"
                        ].append(
                            current_clause
                        )

                        current_section[
                            "page_end"
                        ] = page_number

                        continue

                # ====================================================
                # CONTINUATION
                # ====================================================

                if (
                    current_clause
                    and state == STATE_MAIN
                ):

                    add_block_to_clause(
                        current_clause,
                        block,
                        page_number,
                        text=line,
                    )

                    current_section[
                        "page_end"
                    ] = page_number

    return sections


# ============================================================
# SAVE
# ============================================================

def save_structure(
    data,
    sections
):

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {
        "schema_version": "0.4",

        "document": {
            "number": DOCUMENT_NUMBER,
            "title": DOCUMENT_TITLE,
            "source_file": data[
                "document"
            ].get(
                "source_file"
            ),
            "pages": data[
                "document"
            ].get(
                "pages"
            ),
        },

        "sections": sections,
    }

    # ВАЖНО:
    # encoding=utf-8 + отсутствие BOM.
    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return result


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(
    sections
):

    real_sections = [
        x
        for x in sections
        if x["type"] == "section"
    ]

    appendices = [
        x
        for x in sections
        if x["type"] == "appendix"
    ]

    clauses = []

    for section in real_sections:

        clauses.extend(
            section.get(
                "clauses",
                []
            )
        )

    print()
    print("СТАТИСТИКА")
    print("-" * 60)

    print(
        f"Разделов:    "
        f"{len(real_sections)}"
    )

    print(
        f"Пунктов:     "
        f"{len(clauses)}"
    )

    print(
        f"Приложений:  "
        f"{len(appendices)}"
    )

    print()

    print("РАЗДЕЛЫ")
    print("-" * 60)

    for section in real_sections:

        print(
            f"{section['number']:>2} "
            f"{section['title']} "
            f"| page: "
            f"{section['page_start']}"
        )

    print()

    print("ПРИЛОЖЕНИЯ")
    print("-" * 60)

    for appendix in appendices:

        print(
            f"Приложение "
            f"{appendix['number']} "
            f"{appendix['title']} "
            f"| page: "
            f"{appendix['page_start']}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(
        "VKS Expert AI — "
        "Structure Parser v0.4"
    )
    print("=" * 60)

    print()
    print("Источник:")
    print(INPUT_PATH)

    if not INPUT_PATH.exists():

        print()
        print(
            "ОШИБКА: "
            "исходный JSON не найден."
        )

        return

    # --------------------------------------------------------
    # Читаем исходный JSON
    # --------------------------------------------------------

    with INPUT_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as file:

        data = json.load(file)

    print()
    print(
        "Построение структуры..."
    )

    sections = build_structure(
        data
    )

    result = save_structure(
        data,
        sections
    )

    print()
    print("Готово.")

    print_statistics(
        result["sections"]
    )

    print()
    print("Результат:")
    print(OUTPUT_PATH)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
    