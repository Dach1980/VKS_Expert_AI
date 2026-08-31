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
    DEFAULT_VECTOR_ROOT = PROJECT_ROOT / "data" / "vectordb"

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
        """Единственный фактический каталог хранения векторных индексов."""
        default = self.DEFAULT_VECTOR_ROOT
        try:
            if self.SETTINGS_FILE.exists():
                data = json.loads(self.SETTINGS_FILE.read_text(encoding="utf-8-sig"))
                configured = data.get("vector_index_path")
                if configured:
                    candidate = Path(configured).expanduser()
                    if not candidate.is_absolute():
                        candidate = self.project_root / candidate
                    candidate = candidate.resolve()
                    candidate.mkdir(parents=True, exist_ok=True)
                    return candidate
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        default.mkdir(parents=True, exist_ok=True)
        return default.resolve()

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
        p.write_text(json.dumps({"error": str(error), "error_type": type(error).__name__, "checked_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")

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
                m = re.search(r"((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+)", text)
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
        return result

    @staticmethod
    def _pdf_pages(path: Path) -> int:
        if not path.exists():
            return 0
        try:
            import pymupdf
            with pymupdf.open(path) as document:
                return len(document)
        except Exception:
            try:
                from pypdf import PdfReader
                return len(PdfReader(str(path)).pages)
            except Exception:
                return 0

    def get_version_metadata(self, document_id, version_id=None):
        version = self.get_version(document_id, version_id)
        pdf = self.resolve(version.get("file", ""))
        parsed = self.resolve(version.get("parsed_file", ""))
        result = {"pages_count": int(version.get("pages_count") or self._pdf_pages(pdf))}
        if parsed.exists():
            try:
                data = json.loads(parsed.read_text(encoding="utf-8-sig"))
                result.update(self._extract_parsed_metadata(data))
            except (OSError, json.JSONDecodeError):
                pass
        return result

    def list_statuses(self):
        result = []
        for document in self.registry.get_all_documents():
            versions = document.get("versions", [])
            current = next((v for v in versions if v.get("status") == "current"), None)
            if current is None and versions:
                current = versions[0]
            if current is None:
                continue
            try:
                processing = self._version_processing(document["id"], current["id"])
            except Exception as error:
                processing = {"error": str(error)}
            result.append({
                "document_id": document["id"],
                "number": document.get("number"),
                "title": document.get("title"),
                "version_id": current.get("id"),
                "effective_from": current.get("effective_from"),
                "processing": processing,
                "versions": [self._version_status(document["id"], v) for v in versions],
            })
        return result

    def _version_status(self, document_id, version):
        return {**version, "document_id": document_id, "filename": Path(version.get("file", "")).name, "processing": self._version_processing(document_id, version.get("id"))}

    def _version_processing(self, document_id, version_id):
        p = self.paths(document_id, version_id)
        meta = self.get_version_metadata(document_id, version_id)
        index_file = p.embeddings / "index.faiss"
        metadata_file = p.embeddings / "metadata.json"
        error_file = p.index_root / "index_error.json"
        result = {"pages_count": meta.get("pages_count", 0), "vector_index": index_file.exists(), "vector_metadata": metadata_file.exists()}
        if error_file.exists():
            try:
                result["error"] = json.loads(error_file.read_text(encoding="utf-8")).get("error")
            except Exception:
                result["error"] = "Ошибка индексации"
        return result

    def get_status(self, document_id, version_id=None):
        v = self.get_version(document_id, version_id)
        document = self.get_document(document_id)
        return {**self._version_status(document_id, v), "document": document}
