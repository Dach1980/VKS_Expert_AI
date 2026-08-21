import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STRUCTURED_DIR = PROJECT_ROOT / "knowledge" / "structured"
INDEX_DIR = PROJECT_ROOT / "knowledge" / "index"


class NormativeIndexError(Exception):
    """Ошибка построения нормативного индекса."""
    pass


def load_json(path: Path):
    """
    Загружает JSON.

    utf-8-sig позволяет корректно читать как UTF-8,
    так и UTF-8 с BOM.
    """

    try:
        with open(
            path,
            "r",
            encoding="utf-8-sig"
        ) as file:
            return json.load(file)

    except FileNotFoundError:
        raise NormativeIndexError(
            f"Файл не найден:\n{path}"
        )

    except json.JSONDecodeError as error:
        raise NormativeIndexError(
            f"Ошибка JSON:\n{path}\n{error}"
        )


def save_json(path: Path, data):
    """
    Сохраняет JSON без BOM.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def build_index(structured_data):
    """
    Строит нормативный индекс из structured JSON.
    """

    document = structured_data.get("document", {})

    document_number = document.get("number")
    document_title = document.get("title")

    if not document_number:
        raise NormativeIndexError(
            "В structured JSON отсутствует document.number"
        )

    if not document_title:
        raise NormativeIndexError(
            "В structured JSON отсутствует document.title"
        )

    index = {
        "index_version": "0.1",

        "document": {
            "number": document_number,
            "title": document_title
        },

        "entries": []
    }

    entry_id = 1

    for section in structured_data.get("sections", []):

        section_type = section.get("type")

        section_number = section.get("number")
        section_title = section.get("title")

        # --------------------------------------------------
        # Обычные разделы СП
        # --------------------------------------------------

        if section_type == "section":

            for clause in section.get("clauses", []):

                clause_number = clause.get("number")
                clause_text = clause.get("text")

                if not clause_text:
                    continue

                entry = {
                    "id": entry_id,

                    "type": "clause",

                    "document_number": document_number,

                    "section": {
                        "number": section_number,
                        "title": section_title
                    },

                    "clause": {
                        "number": clause_number,
                        "text": clause_text
                    },

                    "page_start": clause.get("page_start"),
                    "page_end": clause.get("page_end")
                }

                index["entries"].append(entry)

                entry_id += 1

        # --------------------------------------------------
        # Приложения
        # --------------------------------------------------

        elif section_type == "appendix":

            for clause in section.get("clauses", []):

                clause_number = clause.get("number")
                clause_text = clause.get("text")

                if not clause_text:
                    continue

                entry = {
                    "id": entry_id,

                    "type": "appendix_clause",

                    "document_number": document_number,

                    "appendix": {
                        "number": section_number,
                        "title": section_title
                    },

                    "clause": {
                        "number": clause_number,
                        "text": clause_text
                    },

                    "page_start": clause.get("page_start"),
                    "page_end": clause.get("page_end")
                }

                index["entries"].append(entry)

                entry_id += 1

    index["statistics"] = {
        "entries": len(index["entries"])
    }

    return index


def main():

    print("=" * 60)
    print("VKS Expert AI — Normative Index v0.1")
    print("=" * 60)

    print()

    structured_files = list(
        STRUCTURED_DIR.glob("*.json")
    )

    if not structured_files:
        print(
            "ОШИБКА: в каталоге structured "
            "не найдено JSON-файлов."
        )

        raise SystemExit(1)

    for structured_file in structured_files:

        print("Источник:")
        print(structured_file)

        print()
        print("Построение нормативного индекса...")
        print()

        try:
            structured_data = load_json(
                structured_file
            )

            index = build_index(
                structured_data
            )

            output_file = (
                INDEX_DIR /
                structured_file.name
            )

            save_json(
                output_file,
                index
            )

            print("Готово.")
            print()

            print("СТАТИСТИКА")
            print("-" * 60)

            print(
                f"Нормативных единиц: "
                f"{index['statistics']['entries']}"
            )

            print()
            print("Результат:")
            print(output_file)

            print()
            print("=" * 60)
            print()

        except NormativeIndexError as error:

            print()
            print(f"ОШИБКА: {error}")

            raise SystemExit(1)


if __name__ == "__main__":
    main()
    