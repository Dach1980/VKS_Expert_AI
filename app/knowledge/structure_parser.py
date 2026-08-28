"""VKS Expert AI — Structure Parser v1 using KnowledgeStorage."""

import json
import re

from app.knowledge.storage import KnowledgeStorage


EXPECTED_SECTIONS = {
    1: "Область применения", 2: "Нормативные ссылки",
    3: "Термины, определения, обозначения и единицы измерения", 4: "Общие положения",
    5: "Определение расчетных расходов воды, стоков и тепла на приготовление горячей воды",
    6: "Системы холодного водоснабжения", 7: "Противопожарный водопровод",
    8: "Устройство систем холодного водоснабжения", 9: "Системы горячего водоснабжения",
    10: "Устройство систем горячего водоснабжения", 11: "Трубопроводы и арматура",
    12: "Устройства для измерения расхода воды", 13: "Насосные установки",
    14: "Запасные и регулирующие емкости", 15: "Дополнительные требования к системам внутреннего водоснабжения в особых условиях",
    16: "Системы водоотведения", 17: "Санитарно-технические приборы и приемники сточных вод",
    18: "Устройство систем водоотведения", 19: "Расчет внутренней системы водоотведения",
    20: "Местные установки для очистки и перекачки сточных вод", 21: "Внутренние водостоки",
    22: "Дополнительные требования к внутренним системам водоотведения и водостокам в особых условиях",
    23: "Санитарно-эпидемиологические и гигиенические требования, требования охраны",
    24: "Обеспечение надежности и безопасности при эксплуатации. Долговечность и",
    25: "Порядок проведения монтажа и сдачи в эксплуатацию внутренних систем",
    26: "Требования энергетической эффективности внутренних систем водоснабжения и",
}

SECTION_PATTERN = re.compile(r"^(\d{1,2})\s+(.+)$")
CLAUSE_PATTERN = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$")
APPENDIX_PATTERN = re.compile(r"^Приложение\s+([А-ЯЁA-Z])(?:\s+(.*))?$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    text = (text or "").replace("\u00ad", "").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def detect_section(text: str):
    match = SECTION_PATTERN.match(text)
    return {"number": int(match.group(1)), "title": match.group(2).strip()} if match else None


def detect_clause(text: str):
    match = CLAUSE_PATTERN.match(text)
    if not match:
        return None
    number = match.group(1)
    return {"number": number, "text": match.group(2).strip(), "level": number.count(".") + 1}


def detect_appendix(text: str):
    match = APPENDIX_PATTERN.match(text)
    return {"number": match.group(1), "title": (match.group(2) or "").strip()} if match else None


def is_real_section(section):
    if not section or section["number"] not in EXPECTED_SECTIONS:
        return False
    detected = normalize_text(section["title"]).lower()
    expected = normalize_text(EXPECTED_SECTIONS[section["number"]]).lower()
    if detected.startswith(expected[:20]):
        return True
    words = [w for w in re.findall(r"[а-яёa-z]+", expected) if len(w) >= 5]
    return bool(words) and sum(w in detected for w in words) >= min(3, len(words))


def add_block_to_clause(clause, block, page_number, text=None):
    text = normalize_text(block.get("text", "") if text is None else text)
    if not text:
        return
    clause["text"] = f'{clause["text"]} {text}'.strip()
    clause["page_end"] = page_number
    clause["source"]["blocks"].append({"page": page_number, "bbox": block.get("bbox")})


def build_structure(data):
    sections = []
    current_section = None
    current_clause = None
    state = "preamble"
    found_sections = set()
    document = data["document"]

    for page in data.get("pages", []):
        page_number = page["page"]
        for block in page.get("blocks", []):
            for raw_line in block.get("text", "").splitlines():
                line = normalize_text(raw_line)
                if not line:
                    continue

                appendix = detect_appendix(line)
                if appendix:
                    state = "appendix"
                    current_clause = None
                    current_section = {"type": "appendix", "number": appendix["number"], "title": appendix["title"], "page_start": page_number, "page_end": page_number, "blocks": []}
                    sections.append(current_section)
                    continue

                section = detect_section(line)
                if section:
                    number = section["number"]
                    if state == "preamble":
                        if number == 1 and is_real_section(section):
                            state = "main"
                        else:
                            continue
                    if state == "main" and is_real_section(section) and number not in found_sections:
                        current_section = {"type": "section", "number": number, "title": section["title"], "page_start": page_number, "page_end": page_number, "clauses": []}
                        sections.append(current_section)
                        found_sections.add(number)
                        current_clause = None
                        continue

                clause = detect_clause(line)
                if clause and state == "main" and current_section and current_section.get("type") == "section":
                    prefix = f'{current_section["number"]}.'
                    if clause["number"].startswith(prefix):
                        current_clause = {"type": "clause", "number": clause["number"], "level": clause["level"], "text": clause["text"], "page_start": page_number, "page_end": page_number, "source": {"file": document.get("source_file"), "blocks": [{"page": page_number, "bbox": block.get("bbox")}]}}
                        current_section["clauses"].append(current_clause)
                        current_section["page_end"] = page_number
                        continue

                if current_clause and state == "main":
                    add_block_to_clause(current_clause, block, page_number, line)
                    current_section["page_end"] = page_number

    return sections


def save_structure(data, sections, storage, document_id, version_id=None):
    output = storage.structured_path(document_id, version_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {"schema_version": "1.0", "document": {"number": data["document"].get("number"), "title": data["document"].get("title"), "source_file": data["document"].get("source_file"), "pages": data["document"].get("pages")}, "sections": sections}
    with output.open("w", encoding="utf-8", newline="") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return result, output


def main():
    storage = KnowledgeStorage()
    document_id = "SP_30.13330"
    version = storage.get_current_version(document_id)
    input_path = storage.parsed_path(document_id, version["id"])
    if not input_path.exists():
        raise FileNotFoundError(f"Parsed JSON not found: {input_path}")
    with input_path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    sections = build_structure(data)
    result, output = save_structure(data, sections, storage, document_id, version["id"])
    real_sections = [x for x in result["sections"] if x["type"] == "section"]
    clauses = sum((x.get("clauses", []) for x in real_sections), [])
    appendices = [x for x in result["sections"] if x["type"] == "appendix"]
    print(f"Разделов: {len(real_sections)}")
    print(f"Пунктов: {len(clauses)}")
    print(f"Приложений: {len(appendices)}")
    print(f"Результат: {output}")


if __name__ == "__main__":
    main()
