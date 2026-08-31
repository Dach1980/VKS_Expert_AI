"""Project Expert AI — KnowledgeStorage v2."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.registry_manager import DocumentRegistry, RegistryError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StorageError(Exception):
    pass


@dataclass(frozen=True)
class DocumentPaths:
    pdf: Path
    parsed: Path
    structured: Path
    index_root: Path
    pages: Path
    enriched: Path
    chunks: Path
    embeddings: Path


class KnowledgeStorage:
    """Единая файловая модель нормативного документа и его версий."""

    SETTINGS_FILE = PROJECT_ROOT / "knowledge" / "registry" / "storage_settings.json"

    def __init__(self, project_root: Path | str = PROJECT_ROOT, registry: DocumentRegistry | None = None):
        self.project_root = Path(project_root).resolve()
        self.knowledge_root = self.project_root / "knowledge"
        self.registry = registry or DocumentRegistry(self.knowledge_root / "registry" / "documents.json")

    def get_document(self, document_id):
        d = self.registry.get_document(document_id)
        if d is None:
            raise StorageError(f"Документ не найден: {document_id}")
        return d

    def get_version(self, document_id, version_id=None):
        d = self.get_document(document_id)
        if version_id is None:
            try:
                return self.registry.get_current_version(document_id)
            except RegistryError as e:
                raise StorageError(str(e)) from e
        for v in d.get("versions", []):
            if v.get("id") == version_id:
                return v
        raise StorageError(f"Версия {version_id!r} не найдена для {document_id}")

    def get_current_version(self, document_id):
        return self.get_version(document_id)

    def resolve(self, p):
        p = Path(p)
        return p if p.is_absolute() else self.project_root / p

    def vector_index_root(self) -> Path:
        """Фактический каталог хранения векторных индексов."""
        default = self.knowledge_root / "index"
        try:
            if self.SETTINGS_FILE.exists():
                data = json.loads(self.SETTINGS_FILE.read_text(encoding="utf-8-sig"))
                configured = data.get("vector_index_path")
                if configured:
                    candidate = self.resolve(configured)
                    candidate.mkdir(parents=True, exist_ok=True)
                    return candidate
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        default.mkdir(parents=True, exist_ok=True)
        return default

    def set_vector_index_root(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser().resolve()
        candidate.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.SETTINGS_FILE.write_text(
            json.dumps({"vector_index_path": str(candidate)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return candidate

    def get_vector_index_root(self) -> Path:
        return self.vector_index_root()

    def paths(self, document_id, version_id=None):
        v = self.get_version(document_id, version_id)
        root = self.vector_index_root() / document_id / v.get("id", "")
        return DocumentPaths(
            self.resolve(v.get("file", "")),
            self.resolve(v.get("parsed_file", "")),
            self.resolve(v.get("structured_file", "")),
            root,
            root / "pages",
            root / "enriched",
            root / "document_chunks",
            root / "embeddings",
        )

    def ensure_version_dirs(self, document_id, version_id=None):
        p = self.paths(document_id, version_id)
        for d in (p.pages, p.enriched, p.chunks, p.embeddings, p.parsed.parent, p.structured.parent, p.pdf.parent):
            d.mkdir(parents=True, exist_ok=True)
        return p

    def save_pdf(self, document_id, source, version_id=None):
        source = Path(source)
        if not source.exists():
            raise StorageError(f"Исходный PDF не найден: {source}")
        if source.suffix.lower() != ".pdf":
            raise StorageError("KnowledgeStorage принимает только PDF")
        p = self.ensure_version_dirs(document_id, version_id)
        shutil.copy2(source, p.pdf)
        return p.pdf

    def save_uploaded_pdf(self, document_id, upload_file, version_id=None):
        filename = str(getattr(upload_file, "filename", "") or "")
        if not filename.lower().endswith(".pdf"):
            raise StorageError("Поддерживается только загрузка PDF")
        p = self.ensure_version_dirs(document_id, version_id)
        try:
            upload_file.file.seek(0)
            with p.pdf.open("wb") as dst:
                shutil.copyfileobj(upload_file.file, dst)
        except OSError as e:
            raise StorageError(f"Не удалось сохранить PDF: {e}") from e
        return p.pdf

    def _index_error_path(self, document_id, version_id=None):
        return self.paths(document_id, version_id).index_root / "index_error.json"

    def clear_index_error(self, document_id, version_id=None):
        self._index_error_path(document_id, version_id).unlink(missing_ok=True)

    def write_index_error(self, document_id, version_id, error):
        p = self._index_error_path(document_id, version_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"error": str(error), "error_type": type(error).__name__, "checked_at": datetime.now().isoformat()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _walk_strings(value):
        if isinstance(value, dict):
            for k, v in value.items():
                yield str(k), v
                yield from KnowledgeStorage._walk_strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from KnowledgeStorage._walk_strings(v)

    @classmethod
    def _extract_parsed_metadata(cls, data):
        result: dict[str, str] = {}
        strings: list[str] = []
        for key, value in cls._walk_strings(data):
            k = key.lower().strip()
            if not isinstance(value, str):
                continue
            text = value.strip()
            if not text:
                continue
            strings.append(text)
            if k in {"document_number", "norm_number", "normative_number", "standard_number", "number", "code", "document", "standard"}:
                m = re.search(r"((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+)", text, re.I)
                if m:
                    result.setdefault("number", re.sub(r"\s+", " ", m.group(1)).strip())
            if k in {"document_title", "norm_title", "title", "name", "document_name"} and len(text) > 8 and not re.search(r"\.(?:pdf|json)$", text, re.I):
                result.setdefault("title", text)
            if k in {"change_number", "amendment_number", "revision_number", "change", "amendment"}:
                m = re.search(r"(?:№|N|No\.?|номер)?\s*([0-9]+)", text, re.I)
                if m:
                    result.setdefault("change_number", m.group(1))
            if k in {"change_date", "amendment_date", "revision_date"}:
                m = re.search(r"(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", text)
                if m:
                    result.setdefault("change_date", m.group(1))

        if not result.get("number"):
            for text in strings:
                m = re.search(r"\b((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+)\b", text, re.I)
                if m:
                    result["number"] = re.sub(r"\s+", " ", m.group(1)).strip()
                    break
        if not result.get("change_number"):
            for text in strings:
                m = re.search(r"Изменени(?:е|я)\s*(?:№|N|No\.?)?\s*([0-9]+)", text, re.I)
                if m:
                    result["change_number"] = m.group(1)
                    break
        if not result.get("change_date"):
            for text in strings:
                m = re.search(r"Изменени(?:е|я).*?(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
                if m:
                    result["change_date"] = m.group(1)
                    break
        return result

    @staticmethod
    def _pdf_pages(path: Path) -> int:
        if not path.exists():
            return 0
        try:
            from pypdf import PdfReader
            return len(PdfReader(str(path)).pages)
        except Exception:
            try:
                from PyPDF2 import PdfReader
                return len(PdfReader(str(path)).pages)
            except Exception:
                return 0

    @staticmethod
    def _pdf_text(path: Path, max_pages: int = 6) -> str:
        if not path.exists():
            return ""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
        except Exception:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(path))
            except Exception:
                return ""
        parts = []
        for page in reader.pages[:max_pages]:
            try:
                text = page.extract_text() or ""
                if text:
                    parts.append(text)
            except Exception:
                continue
        return "\n".join(parts)

    @classmethod
    def _extract_pdf_metadata(cls, path: Path):
        text = cls._pdf_text(path)
        result: dict[str, str] = {}
        if not text:
            return result
        # Ищем именно полный номер с годом, например СП 30.13330.2020.
        number_matches = re.findall(r"((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+)", text, re.I)
        if number_matches:
            result["number"] = re.sub(r"\s+", " ", max(number_matches, key=len)).strip()
        change = re.search(r"Изменени(?:е|я)\s*(?:№|N|No\.?)?\s*([0-9]+)", text, re.I)
        if change:
            result["change_number"] = change.group(1)
        date_match = re.search(r"(?:Изменени(?:е|я)|Актуализирован|введен(?:а|о)?)?.{0,100}?(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", text, re.I | re.S)
        if date_match:
            result["change_date"] = date_match.group(1)
        # Заголовок обычно находится рядом с первой строкой полного номера.
        for line in (x.strip() for x in text.splitlines()):
            if len(line) < 15 or len(line) > 220:
                continue
            if "внутренний водопровод" in line.lower() and "канализац" in line.lower():
                result.setdefault("title", line)
                break
        return result

    def get_version_metadata(self, document_id, version_id=None):
        v = self.get_version(document_id, version_id)
        p = self.resolve(v.get("parsed_file", ""))
        pdf = self.resolve(v.get("file", ""))
        meta: dict[str, Any] = {}
        candidates = [p]
        stem = Path(v.get("file", "")).stem
        candidates += list((self.knowledge_root / "parsed").glob(f"{stem}*.json"))
        doc_number = str(self.get_document(document_id).get("number", ""))
        if doc_number:
            compact = re.sub(r"[^0-9.]", "", doc_number)
            candidates += list((self.knowledge_root / "parsed").glob(f"*{compact}*.json"))
        for candidate in candidates:
            if candidate.exists():
                try:
                    parsed_meta = self._extract_parsed_metadata(json.loads(candidate.read_text(encoding="utf-8-sig")))
                    if parsed_meta:
                        meta.update(parsed_meta)
                        break
                except (OSError, json.JSONDecodeError):
                    pass
        # PDF — authoritative fallback for old versions without useful JSON metadata.
        pdf_meta = self._extract_pdf_metadata(pdf)
        for key, value in pdf_meta.items():
            if value and (key == "number" or not meta.get(key)):
                meta[key] = value
        for key in ("number", "title", "change_number", "change_date"):
            if v.get(key) and not meta.get(key):
                meta[key] = v[key]
        meta["pages_count"] = int(v.get("pages_count") or self._pdf_pages(pdf))
        return meta

    def get_status(self, document_id, version_id=None):
        document = self.get_document(document_id)
        version = self.get_version(document_id, version_id)
        p = self.paths(document_id, version.get("id"))
        meta = self.get_version_metadata(document_id, version.get("id"))
        page_files = list(p.pages.glob("page_*.json")) if p.pages.exists() else []
        enriched = list(p.enriched.glob("page_*_enriched.json")) if p.enriched.exists() else []
        chunks = p.chunks / "all_chunks.json"
        emb = p.embeddings / "index.faiss"
        emeta = p.embeddings / "metadata.json"
        err = p.index_root / "index_error.json"
        index_error = None
        if err.exists():
            try:
                index_error = json.loads(err.read_text(encoding="utf-8"))
            except Exception:
                index_error = {"error": "Не удалось прочитать сведения об ошибке индексации"}
        return {
            "document_id": document_id,
            "number": meta.get("number") or document.get("number"),
            "title": meta.get("title") or document.get("title"),
            "version_id": version.get("id"),
            "version_type": version.get("type"),
            "status": version.get("status"),
            "effective_from": version.get("effective_from"),
            "change_number": meta.get("change_number"),
            "change_date": meta.get("change_date"),
            "pages_count": meta.get("pages_count", 0),
            "paths": {
                "pdf": str(p.pdf),
                "parsed": str(p.parsed),
                "structured": str(p.structured),
                "pages": str(p.pages),
                "enriched": str(p.enriched),
                "chunks": str(p.chunks),
                "embeddings": str(p.embeddings),
            },
            "processing": {
                "uploaded": p.pdf.exists(),
                "parsed": p.parsed.exists(),
                "structured": p.structured.exists(),
                "pages_indexed": bool(page_files),
                "pages_count": meta.get("pages_count", 0),
                "enriched": bool(enriched),
                "enriched_pages_count": len(enriched),
                "chunks": chunks.exists(),
                "vector_index": emb.exists(),
                "vector_metadata": emeta.exists(),
                "error": index_error,
            },
            "checked_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _document_group_key(number):
        n = re.sub(r"\s+", " ", str(number or "")).strip().lower()
        m = re.search(r"сп\s*[0-9]+\.[0-9]+", n, re.I)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else n

    def list_statuses(self):
        groups = {}
        for d in self.registry.get_all_documents():
            groups.setdefault(self._document_group_key(d.get("number", d.get("id", ""))), []).append(d)
        result = []
        for docs in groups.values():
            enriched_docs = []
            for d in docs:
                dc = dict(d)
                for v in d.get("versions", []):
                    try:
                        m = self.get_version_metadata(d["id"], v.get("id"))
                    except StorageError:
                        m = {}
                    if m.get("number"):
                        dc["number"] = m["number"]
                    if m.get("title"):
                        dc["title"] = m["title"]
                enriched_docs.append(dc)
            canonical = max(enriched_docs, key=lambda x: len(str(x.get("number", ""))))
            current_ref = None
            versions = []
            for d in enriched_docs:
                sid = str(d.get("id"))
                for v in d.get("versions", []):
                    try:
                        s = self.get_status(sid, v.get("id"))
                    except StorageError:
                        continue
                    versions.append({
                        "document_id": sid,
                        "version_id": v.get("id"),
                        "version_type": v.get("type"),
                        "status": v.get("status"),
                        "effective_from": v.get("effective_from"),
                        "change_number": s.get("change_number"),
                        "change_date": s.get("change_date"),
                        "filename": Path(v.get("file", "")).name,
                        "processing": s.get("processing", {}),
                    })
                    if v.get("status") == "current":
                        current_ref = (sid, v)
            if current_ref is None:
                continue
            sid, cv = current_ref
            try:
                current = self.get_status(sid, cv.get("id"))
            except StorageError:
                continue
            current["number"] = canonical.get("number")
            current["title"] = canonical.get("title")
            current["versions"] = versions
            current["current_change_number"] = current.get("change_number")
            current["current_change_date"] = current.get("change_date") or current.get("effective_from")
            result.append(current)
        return sorted(result, key=lambda x: str(x.get("number") or ""))
