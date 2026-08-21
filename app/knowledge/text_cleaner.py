import re


def normalize_spaces(text: str) -> str:
    """
    Нормализация пробелов и переносов строк.
    Смысл текста не изменяется.
    """

    if not text:
        return ""

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    # Неразрывный пробел
    text = text.replace("\xa0", " ")

    # Повторяющиеся пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def remove_repeated_clause_number(
    text: str,
    clause_number: str | None = None,
) -> str:
    """
    Удаляет номер пункта, если он случайно оказался
    в начале текста.

    Например:

    18.19 Диаметр...

    превращается в:

    Диаметр...

    """

    if not text or not clause_number:
        return text

    pattern = rf"^{re.escape(str(clause_number))}\s+"

    return re.sub(
        pattern,
        "",
        text,
        count=1,
    ).strip()


def clean_clause_text(
    text: str,
    clause_number: str | None = None,
) -> str:
    """
    Финальная безопасная очистка текста пункта.
    """

    if not text:
        return ""

    text = normalize_spaces(text)

    text = remove_repeated_clause_number(
        text,
        clause_number,
    )

    return text
