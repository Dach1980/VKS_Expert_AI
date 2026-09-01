"""Project Expert AI — KnowledgeStorage v5."""
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
        root = self.vector_index_root() / document_id / version.get("id", "")
        return DocumentPaths(
            self.resolve(version.get("file", "")),
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
    def _classify_uploaded_filename(filename: str) -> tuple[str | None, str | None]:
        """Определяет тип и номер изменения только по имени загруженного файла."""
        stem = Path(filename).stem.replace("_", " ").replace("-", " ")
        if re.search(r"(?i)\bбазов(?:ая|ую|ая версия)\b|\bбез\s+изменений\b", stem):
            return "base", None
        match = re.search(
            r"(?i)\b(?:изм(?:енение|енения)?|изменени[ея]|amendment)\s*№?\s*(\d+)\b",
            stem,
        )
        if match:
            return "amendment", match.group(1)
        return None, None

    @classmethod
    def _filename_change_number(cls, filename: str | None) -> str | None:
        _, number = cls._classify_uploaded_filename(str(filename or ""))
        return number

    def _apply_filename_version_metadata(self, document_id, version_id, filename):
        version_type, change_number = self._classify_uploaded_filename(filename)
        document = self.registry.get_document(document_id)
        if not document:
            return
        version = next((item for item in document.get("versions", []) if item.get("id") == version_id), None)
        if not version:
            return

        version["original_filename"] = filename
        if version_type == "base":
            version["type"] = "base"
            version.pop("change_number", None)
            version.pop("change_date", None)
        elif version_type == "amendment":
            version["type"] = "amendment"
            version["change_number"] = str(change_number)
            # The amendment number comes from the filename. A date is not
            # inferred from PDF text because that text can reference another amendment.
            version.pop("change_date", None)
        else:
            # A filename without "Изм.N" is an edition without a declared
            # amendment number. Do not inherit stale metadata from parsed JSON.
            version["type"] = "edition"
            version.pop("change_number", None)
            version.pop("change_date", None)
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
        """Extract document number/title only; amendment metadata is filename-owned."""
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
        """Return metadata without allowing parsed PDF text to change amendment number."""
        version = self.get_version(document_id, version_id)
        pdf = self.resolve(version.get("file", ""))
        parsed = self.resolve(version.get("parsed_file", ""))
        filename = version.get("original_filename") or Path(version.get("file", "")).name
        result: dict[str, Any] = {
            "pages_count": int(version.get("pages_count") or self._pdf_pages(pdf)),
        }

        filename_change = self._filename_change_number(filename)
        stored_change = version.get("change_number")
        if filename_change is not None:
            result["change_number"] = filename_change
        elif stored_change is not None:
            result["change_number"] = str(stored_change)

        if version.get("change_date"):
            result["change_date"] = str(version.get("change_date"))
        if version.get("type"):
            result["version_type"] = version.get("type")

        # Parsed JSON may enrich document number/title, but it must never
        # override filename-derived amendment metadata.
        if parsed.exists():
            try:
                parsed_meta = self._extract_parsed_metadata(
                    json.loads(parsed.read_text(encoding="utf-8-sig"))
                )
                result.update(parsed_meta)
                if filename_change is not None:
                    result["change_number"] = filename_change
                elif "change_number" in result and filename_change is None and not stored_change:
                    result.pop("change_number", None)
            except (OSError, json.JSONDecodeError):
                pass
        return result

    def refresh_version_metadata_from_parsed(self, document_id, version_id):
        """Refresh number/title only. Amendment metadata remains controlled by filename."""
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
        if meta.get("title") and document.get("title") != meta["title"]:
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

            # A version is current only when it was explicitly selected by the
            # user. Legacy status="current" without the explicit flag is not
            # treated as an active edition.
            current = next(
                (
                    version
                    for version in versions
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
            result.append(
                {
                    "document_id": document["id"],
                    "number": document.get("number"),
                    "title": document.get("title"),
                    "version_id": current.get("id") if current else None,
                    "effective_from": current.get("effective_from") if current else None,
                    "current_change_number": current_meta.get("change_number"),
                    "current_change_date": current_meta.get("change_date") or (current.get("effective_from") if current else None),
                    "processing": processing,
                    "versions": [self._version_status(document["id"], version) for version in versions],
                }
            )
        return result

    def _version_status(self, document_id, version):
        filename = version.get("original_filename") or Path(version.get("file", "")).name
        return {
            **version,
            "document_id": document_id,
            "version_id": version.get("id"),
            "filename": filename,
            "original_filename": version.get("original_filename") or filename,
            "processing": self._version_processing(document_id, version.get("id")),
        }

    def _version_processing(self, document_id, version_id):
        paths = self.paths(document_id, version_id)
        meta = self.get_version_metadata(document_id, version_id)
        index_file = paths.embeddings / "index.faiss"
        metadata_file = paths.embeddings / "metadata.json"
        error_file = paths.index_root / "index_error.json"
        indexing_file = paths.index_root / "indexing.json"
        result = {
            "pages_count": meta.get("pages_count", 0),
            "vector_index": index_file.exists(),
            "vector_metadata": metadata_file.exists(),
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
