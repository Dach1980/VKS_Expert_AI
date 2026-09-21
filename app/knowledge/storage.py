"""Project Expert AI — KnowledgeStorage v6."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.filename_parser import FilenameParseError, parse_normative_filename
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
        document = self.registry.get_document(document_id)
        if document is None:
            raise StorageError(f"Документ не найден: {document_id}")
        return document

    def get_version(self, document_id, version_id=None):
        document = self.get_document(document_id)
        if version_id is None:
            try:
                return self.registry.get_current_version(document_id)
            except RegistryError as error:
                raise StorageError(str(error)) from error
        for version in document.get("versions", []):
            if version.get("id") == version_id:
                return version
        raise StorageError(f"Версия {version_id!r} не найдена для {document_id}")

    def get_current_version(self, document_id):
        return self.get_version(document_id)

    def resolve(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.project_root / path

    def vector_index_root(self) -> Path:
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
        version = self.get_version(document_id, version_id)
        document = self.get_document(document_id)
        document_number = document.get("number") or document_id
        document_number = document_number.replace(" ", "_")
        root = self.vector_index_root() / document_number / version.get("id", "")
        source = version.get("source") or {}
        return DocumentPaths(
            self.resolve(source.get("file", "")),
            self.resolve(version.get("parsed_file", "")),
            self.resolve(version.get("structured_file", "")),
            root,
            root / "pages",
            root / "enriched",
            root / "document_chunks",
            root / "embeddings",
        )

    def ensure_version_dirs(self, document_id, version_id=None):
        paths = self.paths(document_id, version_id)
        for directory in (
            paths.pages,
            paths.enriched,
            paths.chunks,
            paths.embeddings,
            paths.parsed.parent,
            paths.structured.parent,
            paths.pdf.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return paths

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _apply_filename_version_metadata(self, document_id, version_id, filename):
        """Обновляет canonical edition/source поля из имени PDF."""
        document = self.registry.get_document(document_id)
        if not document:
            return
        version = next((item for item in document.get("versions", []) if item.get("id") == version_id), None)
        if not version:
            return
        try:
            parsed = parse_normative_filename(filename)
        except FilenameParseError as error:
            raise StorageError(str(error)) from error

        edition = version.setdefault("edition", {})
        if parsed.effective_date:
            edition["date"] = parsed.effective_date
        else:
            edition.pop("date", None)
        if parsed.amendment_number is not None:
            edition["amendment"] = {"number": parsed.amendment_number}
            if parsed.effective_date:
                edition["amendment"]["effective_from"] = parsed.effective_date
        else:
            edition.pop("amendment", None)

        source = version.setdefault("source", {})
        source["original_filename"] = parsed.original_filename
        self.registry.save()

    def save_pdf(self, document_id, source, version_id=None):
        source = Path(source)
        if not source.exists():
            raise StorageError(f"Исходный PDF не найден: {source}")
        if source.suffix.lower() != ".pdf":
            raise StorageError("KnowledgeStorage принимает только PDF")
        paths = self.ensure_version_dirs(document_id, version_id)
        shutil.copy2(source, paths.pdf)
        self._apply_filename_version_metadata(document_id, version_id, source.name)
        version = self.get_version(document_id, version_id)
        version.setdefault("source", {})["sha256"] = self._sha256(paths.pdf)
        self.registry.save()
        return paths.pdf

    def save_uploaded_pdf(self, document_id, upload_file, version_id=None):
        filename = str(getattr(upload_file, "filename", "") or "")
        if not filename.lower().endswith(".pdf"):
            raise StorageError("Поддерживается только загрузка PDF")
        paths = self.ensure_version_dirs(document_id, version_id)
        try:
            upload_file.file.seek(0)
            with paths.pdf.open("wb") as destination:
                shutil.copyfileobj(upload_file.file, destination)
        except OSError as error:
            raise StorageError(f"Не удалось сохранить PDF: {error}") from error
        self._apply_filename_version_metadata(document_id, version_id, filename)
        version = self.get_version(document_id, version_id)
        version.setdefault("source", {})["sha256"] = self._sha256(paths.pdf)
        self.registry.save()
        return paths.pdf

    def _index_error_path(self, document_id, version_id=None):
        return self.paths(document_id, version_id).index_root / "index_error.json"

    def _indexing_marker_path(self, document_id, version_id=None):
        return self.paths(document_id, version_id).index_root / "indexing.json"

    def start_indexing(self, document_id, version_id):
        path = self._indexing_marker_path(document_id, version_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"started_at": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False),
            encoding="utf-8",
        )

    def finish_indexing(self, document_id, version_id):
        self._indexing_marker_path(document_id, version_id).unlink(missing_ok=True)

    def clear_index_error(self, document_id, version_id=None):
        self._index_error_path(document_id, version_id).unlink(missing_ok=True)

    def write_index_error(self, document_id, version_id, error):
        path = self._index_error_path(document_id, version_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
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
            for key, child in value.items():
                yield str(key), child
                yield from KnowledgeStorage._walk_strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from KnowledgeStorage._walk_strings(child)

    @classmethod
    def _extract_parsed_metadata(cls, data):
        """Извлекает номер/название; edition metadata принадлежит имени файла."""
        result: dict[str, str] = {}
        for key, value in cls._walk_strings(data):
            normalized_key = key.lower().strip()
            if not isinstance(value, str):
                continue
            text = value.strip()
            if not text:
                continue
            if normalized_key in {
                "document_number", "norm_number", "normative_number", "standard_number", "number", "code"
            }:
                match = re.search(r"((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+)", text)
                if match:
                    result.setdefault("number", re.sub(r"\s+", " ", match.group(1)).strip())
            if normalized_key in {"document_title", "norm_title", "title", "name", "document_name"}:
                if len(text) > 8 and not re.search(r"\.(?:pdf|json)$", text, re.I):
                    result.setdefault("title", text)
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
        """Возвращает canonical metadata версии."""
        version = self.get_version(document_id, version_id)
        source = version.get("source") or {}
        pdf = self.resolve(source.get("file", ""))
        result: dict[str, Any] = {
            "edition": dict(version.get("edition") or {}),
            "source": dict(source),
            "pages_count": int((version.get("index") or {}).get("pages_count") or self._pdf_pages(pdf)),
            "version_type": version.get("version_type") or "edition",
        }
        parsed = self.resolve(version.get("parsed_file", ""))
        if parsed.exists():
            try:
                result.update(self._extract_parsed_metadata(json.loads(parsed.read_text(encoding="utf-8-sig"))))
            except (OSError, json.JSONDecodeError):
                pass
        return result

    def refresh_version_metadata_from_parsed(self, document_id, version_id):
        version = self.get_version(document_id, version_id)
        parsed = self.resolve(version.get("parsed_file", ""))
        if not parsed.exists():
            return {}
        try:
            data = json.loads(parsed.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}
        meta = self._extract_parsed_metadata(data)
        changed = False
        document = self.registry.get_document(document_id)
        if meta.get("number") and meta["number"] != document.get("number"):
            document["number"] = meta["number"]
            changed = True
        if meta.get("title") and meta["title"] != document.get("title"):
            document["title"] = meta["title"]
            changed = True
        if changed:
            self.registry.save()
        return meta

    def list_statuses(self):
        result = []
        for document in self.registry.get_all_documents():
            versions = document.get("versions", [])
            if not versions:
                continue
            current = next(
                (
                    version for version in versions
                    if version.get("status") == "current"
                    and version.get("current_selected_by_user") is True
                ),
                None,
            )
            processing = (
                self._version_processing(document["id"], current["id"])
                if current
                else {"pages_count": 0, "vector_index": False, "vector_metadata": False, "indexing": False}
            )
            current_meta = self.get_version_metadata(document["id"], current["id"]) if current else {}
            result.append({
                "document_id": document["id"],
                "number": document.get("number"),
                "title": document.get("title"),
                "document_type": document.get("document_type"),
                "version_id": current.get("id") if current else None,
                "edition": current_meta.get("edition", {}),
                "source": current_meta.get("source", {}),
                "processing": processing,
                "versions": [self._version_status(document["id"], version) for version in versions],
            })
        return result

    def _version_status(self, document_id, version):
        source = version.get("source") or {}
        filename = source.get("original_filename") or Path(source.get("file", "")).name
        return {
            **version,
            "document_id": document_id,
            "version_id": version.get("id"),
            "filename": filename,
            "processing": self._version_processing(document_id, version.get("id")),
        }

    def _version_processing(self, document_id, version_id):
        paths = self.paths(document_id, version_id)
        meta = self.get_version_metadata(document_id, version_id)
        error_file = paths.index_root / "index_error.json"
        indexing_file = paths.index_root / "indexing.json"
        result = {
            "pages_count": meta.get("pages_count", 0),
            "vector_index": (paths.embeddings / "index.faiss").exists(),
            "vector_metadata": (paths.embeddings / "metadata.json").exists(),
            "indexing": indexing_file.exists(),
        }
        if error_file.exists():
            try:
                result["error"] = json.loads(error_file.read_text(encoding="utf-8")).get("error")
            except Exception:
                result["error"] = "Ошибка индексации"
        return result

    def get_status(self, document_id, version_id=None):
        version = self.get_version(document_id, version_id)
        document = self.get_document(document_id)
        return {**self._version_status(document_id, version), "document": document}
