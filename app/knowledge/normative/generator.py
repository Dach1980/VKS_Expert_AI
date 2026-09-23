"""Generate canonical Normative JSON 2.0 from a normative PDF extraction.

The generator deliberately keeps semantic extraction conservative. It builds
document structure and provenance from PDFPageProcessor output and only creates
a requirement when the source text contains an explicit normative cue. It
never invents numeric values, applicability, operators, or table contents.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.filename_parser import FilenameParseError, parse_normative_filename
from app.knowledge.normative.validator import NormativeJSONValidator
from app.knowledge.storage import KnowledgeStorage


SECTION_RE = re.compile(r"^(\d{1,3})\s+(.+)$")
CLAUSE_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+)$")
APPENDIX_RE = re.compile(r"^Приложение\s+([А-ЯЁA-Z0-9]+)(?:\s*[—-]\s*(.*)|\s+(.*))?$", re.IGNORECASE)
REFERENCE_CLAUSE_RE = re.compile(r"(?:п\.|пункт(?:а|ом)?|раздел(?:а|ом)?)\s*(\d+(?:\.\d+)*)", re.IGNORECASE)
STANDARD_RE = re.compile(r"\b((?:СП|ГОСТ(?:\s+Р)?|СНиП|ТР)\s*[0-9]+(?:\.[0-9]+)+(?:\.[0-9]{4})?)\b", re.IGNORECASE)

MANDATORY_RE = re.compile(
    r"\b(должен|должна|должно|должны|следует|необходимо|обязательн(?:о|ый|ая|ые)|"
    r"не допускается|запрещается|требуется)\b",
    re.IGNORECASE,
)
CONDITIONAL_RE = re.compile(r"\b(при|если|в случае|при условии|при наличии|когда)\b", re.IGNORECASE)
RECOMMENDATION_RE = re.compile(r"\b(рекомендуется|как правило|целесообразно|может быть)\b", re.IGNORECASE)


class NormativeGenerationError(RuntimeError):
    pass


class NormativeJSONGenerator:
    """Build Normative JSON 2.0 from one registered normative version."""

    VERSION = "0.1.0"

    def __init__(self, document_id: str, version_id: str, storage: KnowledgeStorage | None = None):
        self.document_id = document_id
        self.version_id = version_id
        self.storage = storage or KnowledgeStorage()

    @property
    def paths(self):
        return self.storage.paths(self.document_id, self.version_id)

    @property
    def status_path(self) -> Path:
        return self.paths.index_root / "normative_generation.json"

    def _status(self, stage: str, status: str = "running", **extra: Any) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "status": status,
            "stage": stage,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            **extra,
        }
        self.status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _text(value: Any) -> str:
        return re.sub(r"[\\u00a0\\u00ad\\u202f]+", " ", str(value or "")).strip()

    @classmethod
    def _source(cls, file_name: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "file": file_name,
            "blocks": [
                {"page": int(item["page"]), "bbox": [float(v) for v in item["bbox"]]}
                for item in blocks
                if item.get("page") is not None and isinstance(item.get("bbox"), (list, tuple)) and len(item["bbox"]) == 4
            ],
        }

    @staticmethod
    def _source_blocks(page: dict[str, Any], block: dict[str, Any]) -> list[dict[str, Any]]:
        bbox = block.get("bbox") or [0, 0, page.get("geometry", {}).get("width", 0), page.get("geometry", {}).get("height", 0)]
        return [{"page": int(page.get("page", 1)), "bbox": bbox}]

    def _load_pages(self) -> dict[str, Any]:
        if not self.paths.parsed.exists():
            raise NormativeGenerationError(
                f"Распарсенный PDF не найден: {self.paths.parsed}. "
                "Генератор должен запускаться после PDFPageProcessor."
            )
        try:
            return json.loads(self.paths.parsed.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise NormativeGenerationError(f"Не удалось прочитать parsed JSON: {error}") from error

    def _document_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        document = self.storage.get_document(self.document_id)
        version = self.storage.get_version(self.document_id, self.version_id)
        source = version.get("source") or {}
        filename = source.get("original_filename") or Path(source.get("file", "")).name

        try:
            parsed_name = parse_normative_filename(filename)
        except FilenameParseError:
            parsed_name = None

        number = document.get("number") or (parsed_name.document_number if parsed_name else None)
        if not number:
            number = data.get("document", {}).get("number") or self.document_id

        title = document.get("title") or data.get("document", {}).get("title") or number
        match = re.search(r"(19|20|21|22)\\d{2}", number)
        base_year = int(match.group(0)) if match else datetime.now().year

        edition_data = version.get("edition") or {}
        edition_date = edition_data.get("date") or (parsed_name.effective_date if parsed_name else None)
        amendments = []
        amendment = edition_data.get("amendment")
        if amendment and amendment.get("number") is not None and (amendment.get("effective_from") or edition_date):
            amendments.append({
                "number": int(amendment["number"]),
                "effective_from": str(amendment.get("effective_from") or edition_date),
            })
        label = filename or str(number)

        pages_count = len(data.get("pages", [])) or int(version.get("pages_count") or 0)
        source_result = {
            "file": str(source.get("file") or ""),
            "original_filename": str(filename),
            "pages": max(1, pages_count),
        }
        sha256 = source.get("sha256") or version.get("sha256")
        if sha256:
            source_result["sha256"] = str(sha256)
        return {
            "document": {
                "document_id": self.document_id,
                "number": str(number),
                "title": str(title),
                "document_type": str(document.get("document_type") or "СП"),
                "edition": {
                    "id": self.version_id,
                    "label": label,
                    "base_year": base_year,
                    "amendments": amendments,
                },
                "source": source_result,
            }
        }

    @classmethod
    def _is_section(cls, text: str) -> re.Match | None:
        match = SECTION_RE.match(text)
        if not match or "." in match.group(1):
            return None
        return match

    @classmethod
    def _is_clause(cls, text: str) -> re.Match | None:
        return CLAUSE_RE.match(text)

    @classmethod
    def _is_appendix(cls, text: str) -> re.Match | None:
        return APPENDIX_RE.match(text)

    @classmethod
    def _requirement_type(cls, text: str) -> str | None:
        if not MANDATORY_RE.search(text) and not RECOMMENDATION_RE.search(text):
            return None
        if RECOMMENDATION_RE.search(text) and not MANDATORY_RE.search(text):
            return "recommendation"
        if CONDITIONAL_RE.search(text):
            return "conditional"
        return "mandatory"

    @staticmethod
    def _requirement_subject(clause_number: str) -> dict[str, str]:
        return {"object": f"требование пункта {clause_number}"}

    def _build(self, data: dict[str, Any]) -> dict[str, Any]:
        meta = self._document_metadata(data)
        source_file = meta["document"]["source"]["original_filename"]

        sections: list[dict[str, Any]] = []
        appendices: list[dict[str, Any]] = []
        requirements: list[dict[str, Any]] = []
        references: list[dict[str, Any]] = []
        tables: list[dict[str, Any]] = []

        current_section: dict[str, Any] | None = None
        current_clause: dict[str, Any] | None = None
        current_appendix: dict[str, Any] | None = None
        seen_refs: set[str] = set()

        for page in data.get("pages", []):
            page_number = int(page.get("page", 1))
            for block in page.get("blocks", []):
                raw = self._text(block.get("text"))
                if not raw:
                    continue
                source_blocks = self._source_blocks(page, block)
                lines = [self._text(line) for line in raw.splitlines() if self._text(line)]

                for line in lines:
                    appendix_match = self._is_appendix(line)
                    section_match = self._is_section(line)
                    clause_match = self._is_clause(line)

                    if appendix_match:
                        number = appendix_match.group(1)
                        title = self._text(appendix_match.group(2) or appendix_match.group(3) or "")
                        current_appendix = {
                            "number": number,
                            "title": title,
                            "page_start": page_number,
                            "page_end": page_number,
                            "source": self._source(source_file, source_blocks),
                            "requirements": [],
                            "tables": [],
                            "references": [],
                        }
                        appendices.append(current_appendix)
                        current_section = None
                        current_clause = None
                        continue

                    if section_match and not clause_match:
                        number, title = section_match.group(1), self._text(section_match.group(2))
                        current_section = {
                            "number": number,
                            "title": title,
                            "page_start": page_number,
                            "page_end": page_number,
                            "source": self._source(source_file, source_blocks),
                            "clauses": [],
                        }
                        sections.append(current_section)
                        current_clause = None
                        current_appendix = None
                        continue

                    if clause_match:
                        number, text = clause_match.group(1), self._text(clause_match.group(2))
                        level = number.count(".") + 1
                        current_clause = {
                            "number": number,
                            "level": level,
                            "text": text,
                            "page_start": page_number,
                            "page_end": page_number,
                            "source": self._source(source_file, source_blocks),
                            "requirements": [],
                            "table_refs": [],
                            "references": [],
                        }
                        if current_section is not None:
                            current_section["clauses"].append(current_clause)
                            current_section["page_end"] = page_number
                        elif current_appendix is not None:
                            current_appendix["page_end"] = page_number

                        req_type = self._requirement_type(current_clause["text"])
                        if req_type and not current_clause["requirements"]:
                            req_id = f"{self.document_id}:{self.version_id}:req:{current_clause['number']}"
                            requirement = {
                                "requirement_id": req_id,
                                "clause_id": current_clause["number"],
                                "text": current_clause["text"],
                                "type": req_type,
                                "subject": self._requirement_subject(current_clause["number"]),
                                "source": current_clause["source"],
                            }
                            requirements.append(requirement)
                            current_clause["requirements"].append(req_id)

                        for match in STANDARD_RE.finditer(current_clause["text"]):
                            target_number = re.sub(r"\s+", " ", match.group(1)).strip()
                            ref_id = f"{self.document_id}:{self.version_id}:ref:std:{target_number.lower().replace(' ', '_')}"
                            if ref_id not in seen_refs:
                                seen_refs.add(ref_id)
                                references.append({
                                    "reference_id": ref_id,
                                    "type": "standard_reference",
                                    "target": {"document_number": target_number},
                                    "source": current_clause["source"],
                                })
                                current_clause["references"].append(ref_id)
                        continue

                    if current_clause is not None:
                        current_clause["text"] = self._text(current_clause["text"] + " " + line)
                        current_clause["page_end"] = page_number
                        current_clause["source"]["blocks"].extend(self._source(source_file, source_blocks)["blocks"])
                    elif current_section is not None:
                        current_section["page_end"] = page_number
                    elif current_appendix is not None:
                        current_appendix["page_end"] = page_number

                    if current_clause is not None:
                        req_type = self._requirement_type(current_clause["text"])
                        if req_type and not current_clause["requirements"]:
                            req_id = f"{self.document_id}:{self.version_id}:req:{current_clause['number']}"
                            requirement = {
                                "requirement_id": req_id,
                                "clause_id": current_clause["number"],
                                "text": current_clause["text"],
                                "type": req_type,
                                "subject": self._requirement_subject(current_clause["number"]),
                                "source": current_clause["source"],
                            }
                            requirements.append(requirement)
                            current_clause["requirements"].append(req_id)

                        for match in STANDARD_RE.finditer(current_clause["text"]):
                            target_number = re.sub(r"\\s+", " ", match.group(1)).strip()
                            ref_id = f"{self.document_id}:{self.version_id}:ref:std:{target_number.lower().replace(' ', '_')}"
                            if ref_id in seen_refs:
                                continue
                            seen_refs.add(ref_id)
                            reference = {
                                "reference_id": ref_id,
                                "type": "standard_reference",
                                "target": {"document_number": target_number},
                                "source": current_clause["source"],
                            }
                            references.append(reference)
                            current_clause["references"].append(ref_id)

        # Normalize ranges and remove empty provenance duplicates.
        for section in sections:
            section["page_end"] = max(section["page_start"], section["page_end"])
            for clause in section["clauses"]:
                clause["page_end"] = max(clause["page_start"], clause["page_end"])
                clause["source"]["blocks"] = self._unique_blocks(clause["source"]["blocks"])
        for appendix in appendices:
            appendix["page_end"] = max(appendix["page_start"], appendix["page_end"])
        for requirement in requirements:
            requirement["source"]["blocks"] = self._unique_blocks(requirement["source"]["blocks"])
        for reference in references:
            reference["source"]["blocks"] = self._unique_blocks(reference["source"]["blocks"])

        return {
            "schema_version": "2.0",
            **meta,
            "structure": {"sections": sections, "appendices": appendices},
            "requirements": requirements,
            "tables": tables,
            "references": references,
            "provenance": {
                "generator": {"name": "NormativeJSONGenerator", "version": self.VERSION},
                "source_format": "pdf",
                "extraction": {
                    "pipeline": ["PyMuPDF", "PDFPageProcessor", "NormativeJSONGenerator"]
                },
            },
        }

    @staticmethod
    def _unique_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        seen = set()
        for block in blocks:
            key = (block.get("page"), tuple(block.get("bbox") or []))
            if key in seen:
                continue
            seen.add(key)
            result.append(block)
        return result

    def generate(self) -> tuple[dict[str, Any], Any]:
        self._status("loading", pages=0)
        data = self._load_pages()
        pages = len(data.get("pages", []))
        self._status("structure", pages=pages)

        document = self._build(data)
        self._status(
            "validation",
            pages=pages,
            sections=len(document["structure"]["sections"]),
            appendices=len(document["structure"]["appendices"]),
            clauses=sum(len(s["clauses"]) for s in document["structure"]["sections"]),
            requirements=len(document["requirements"]),
            tables=len(document["tables"]),
            references=len(document["references"]),
        )

        schema_path = Path(__file__).resolve().parents[3] / "training" / "schemas" / "normative_document.schema.json"
        result = NormativeJSONValidator(schema_path).validate(document)

        output = self.paths.structured
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

        if result.valid:
            self._status(
                "complete",
                status="validated",
                valid=True,
                output=str(output),
                statistics={
                    "pages": pages,
                    "sections": len(document["structure"]["sections"]),
                    "appendices": len(document["structure"]["appendices"]),
                    "clauses": sum(len(s["clauses"]) for s in document["structure"]["sections"]),
                    "requirements": len(document["requirements"]),
                    "tables": len(document["tables"]),
                    "references": len(document["references"]),
                },
            )
        else:
            self._status(
                "complete",
                status="failed",
                valid=False,
                errors=[e.__dict__ for e in result.errors],
            )
        return document, result
