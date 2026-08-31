"""Project Expert AI — KnowledgeStorage v1."""

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
    """Ошибка работы с KnowledgeStorage."""


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
    """Единая точка доступа к путям нормативных документов."""
    def __init__(self, project_root: Path | str = PROJECT_ROOT, registry: DocumentRegistry | None = None) -> None:
        self.project_root = Path(project_root).resolve()
        self.knowledge_root = self.project_root / "knowledge"
        self.registry = registry or DocumentRegistry(self.knowledge_root / "registry" / "documents.json")

    def get_document(self, document_id: str) -> dict[str, Any]:
        document = self.registry.get_document(document_id)
        if document is None:
            raise StorageError(f"Документ не найден: {document_id}")
        return document

    def get_version(self, document_id: str, version_id: str | None = None) -> dict[str, Any]:
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

    def get_current_version(self, document_id: str) -> dict[str, Any]:
        return self.get_version(document_id)

    def resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        return path if path.is_absolute() else self.project_root / path

    def paths(self, document_id: str, version_id: str | None = None) -> DocumentPaths:
        version = self.get_version(document_id, version_id)
        index_root = self.knowledge_root / "index" / document_id / version.get("id", "")
        return DocumentPaths(
            pdf=self.resolve(version.get("file", "")),
            parsed=self.resolve(version.get("parsed_file", "")),
            structured=self.resolve(version.get("structured_file", "")),
            index_root=index_root,
            pages=index_root / "pages",
            enriched=index_root / "enriched",
            chunks=index_root / "document_chunks",
            embeddings=index_root / "embeddings",
        )

    def pdf_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).pdf

    def parsed_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).parsed

    def structured_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).structured

    def pages_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).pages

    def enriched_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).enriched

    def chunks_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).chunks

    def embeddings_dir(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).embeddings

    def ensure_version_dirs(self, document_id: str, version_id: str | None = None) -> DocumentPaths:
        paths = self.paths(document_id, version_id)
        for directory in (paths.pages, paths.enriched, paths.chunks, paths.embeddings, paths.parsed.parent, paths.structured.parent, paths.pdf.parent):
            directory.mkdir(parents=True, exist_ok=True)
        return paths

    def save_pdf(self, document_id: str, source: Path | str, version_id: str | None = None) -> Path:
        source_path = Path(source)
        if not source_path.exists():
            raise StorageError(f"Исходный PDF не найден: {source_path}")
        if source_path.suffix.lower() != ".pdf":
            raise StorageError("KnowledgeStorage принимает только PDF")
        paths = self.ensure_version_dirs(document_id, version_id)
        shutil.copy2(source_path, paths.pdf)
        return paths.pdf

    def save_uploaded_pdf(self, document_id: str, upload_file, version_id: str | None = None) -> Path:
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
        return paths.pdf

    def _index_error_path(self, document_id: str, version_id: str | None = None) -> Path:
        return self.paths(document_id, version_id).index_root / "index_error.json"

    def clear_index_error(self, document_id: str, version_id: str | None = None) -> None:
        self._index_error_path(document_id, version_id).unlink(missing_ok=True)

    def write_index_error(self, document_id: str, version_id: str, error: Exception) -> None:
        path = self._index_error_path(document_id, version_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump({"error": str(error), "error_type": type(error).__name__, "checked_at": datetime.now().isoformat()}, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _walk_strings(value: Any):
        if isinstance(value, dict):
            for key, item in value.items():
                yield str(key), item
                yield from KnowledgeStorage._walk_strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from KnowledgeStorage._walk_strings(item)

    @classmethod
    def _extract_parsed_metadata(cls, data: Any) -> dict[str, Any]:
        """Извлечь человекочитаемые реквизиты из parsed JSON без привязки к одной схеме парсера."""
        result: dict[str, Any] = {}
        strings: list[str] = []
        preferred_number_keys = {"document_number", "norm_number", "normative_number", "standard_number", "number", "code"}
        preferred_title_keys = {"document_title", "norm_title", "title", "name"}
        preferred_change_keys = {"change_number", "amendment_number", "revision_number", "change", "amendment"}
        preferred_date_keys = {"change_date", "amendment_date", "revision_date"}

        for key, value in cls._walk_strings(data):
            key_lower = key.lower().strip()
            if isinstance(value, str):
                text = value.strip()
                if text:
                    strings.append(text)
                    if "number" in result and "title" in result and "change_number" in result and "change_date" in result:
                        continue
                    if key_lower in preferred_number_keys and re.search(r"(?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*\d+(?:\.\d+)+", text, re.IGNORECASE):
                        result.setdefault("number", re.sub(r"\s+", " ", text))
                    if key_lower in preferred_title_keys and len(text) > 8 and not re.search(r"\.(?:pdf|json)$", text, re.IGNORECASE):
                        result.setdefault("title", text)
                    if key_lower in preferred_change_keys:
                        match = re.search(r"(?:№|N|No\.?|номер)?\s*([0-9]+)", text, re.IGNORECASE)
                        if match:
                            result.setdefault("change_number", match.group(1))
                    if key_lower in preferred_date_keys:
                        match = re.search(r"\b(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})\b", text)
                        if match:
                            result.setdefault("change_date", match.group(1))

        if not result.get("number"):
            for text in strings:
                match = re.search(r"\b((?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*\d+(?:\.\d+)+)\b", text, re.IGNORECASE)
                if match:
                    result["number"] = re.sub(r"\s+", " ", match.group(1)).strip()
                    break

        if not result.get("change_number"):
            for text in strings:
                match = re.search(r"Изменени(?:е|я)\s*(?:№|N|No\.?)?\s*([0-9]+)", text, re.IGNORECASE)
                if match:
                    result["change_number"] = match.group(1)
                    break

        if not result.get("change_date"):
            for text in strings:
                match = re.search(r"Изменени(?:е|я).*?(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
                if match:
                    result["change_date"] = match.group(1)
                    break

        return result

    def get_version_metadata(self, document_id: str, version_id: str | None = None) -> dict[str, Any]:
        """Вернуть метаданные версии, прежде всего реквизиты из parsed JSON."""
        version = self.get_version(document_id, version_id)
        parsed_path = self.resolve(version.get("parsed_file", ""))
        metadata: dict[str, Any] = {}
        if parsed_path.exists():
            try:
                with parsed_path.open("r", encoding="utf-8-sig") as file:
                    metadata = self._extract_parsed_metadata(json.load(file))
            except (OSError, json.JSONDecodeError):
                metadata = {}
        return metadata

    def get_status(self, document_id: str, version_id: str | None = None) -> dict[str, Any]:
        document = self.get_document(document_id)
        version = self.get_version(document_id, version_id)
        paths = self.paths(document_id, version.get("id"))
        metadata = self.get_version_metadata(document_id, version.get("id"))
        page_files = list(paths.pages.glob("page_*.json")) if paths.pages.exists() else []
        enriched_files = list(paths.enriched.glob("page_*_enriched.json")) if paths.enriched.exists() else []
        chunks_file = paths.chunks / "all_chunks.json"
        embeddings_file = paths.embeddings / "index.faiss"
        metadata_file = paths.embeddings / "metadata.json"
        error_file = paths.index_root / "index_error.json"
        index_error = None
        if error_file.exists():
            try:
                with error_file.open("r", encoding="utf-8") as file:
                    index_error = json.load(file)
            except (OSError, json.JSONDecodeError):
                index_error = {"error": "Не удалось прочитать сведения об ошибке индексации"}
        return {
            "document_id": document_id,
            "number": metadata.get("number") or document.get("number"),
            "title": metadata.get("title") or document.get("title"),
            "version_id": version.get("id"),
            "version_type": version.get("type"),
            "status": version.get("status"),
            "effective_from": version.get("effective_from"),
            "change_number": metadata.get("change_number"),
            "change_date": metadata.get("change_date"),
            "paths": {
                "pdf": str(paths.pdf),
                "parsed": str(paths.parsed),
                "structured": str(paths.structured),
                "pages": str(paths.pages),
                "enriched": str(paths.enriched),
                "chunks": str(paths.chunks),
                "embeddings": str(paths.embeddings),
            },
            "processing": {
                "uploaded": paths.pdf.exists(),
                "parsed": paths.parsed.exists(),
                "structured": paths.structured.exists(),
                "pages_indexed": bool(page_files),
                "pages_count": len(page_files),
                "enriched": bool(enriched_files),
                "enriched_pages_count": len(enriched_files),
                "chunks": chunks_file.exists(),
                "vector_index": embeddings_file.exists(),
                "vector_metadata": metadata_file.exists(),
                "error": index_error,
            },
            "checked_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _document_group_key(number: str) -> str:
        normalized = re.sub(r"\s+", " ", str(number or "")).strip().lower()
        match = re.search(r"сп\s*[0-9]+\.[0-9]+", normalized, re.IGNORECASE)
        return re.sub(r"\s+", " ", match.group(0)).strip() if match else normalized

    def list_statuses(self) -> list[dict[str, Any]]:
        """Одна карточка на логический СП; все его редакции находятся внутри карточки."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for document in self.registry.get_all_documents():
            groups.setdefault(self._document_group_key(document.get("number", document.get("id", ""))), []).append(document)

        result = []
        for documents in groups.values():
            enriched_documents = []
            for document in documents:
                doc_copy = dict(document)
                doc_number = document.get("number")
                doc_title = document.get("title")
                for version in document.get("versions", []):
                    try:
                        meta = self.get_version_metadata(document["id"], version.get("id"))
                    except StorageError:
                        meta = {}
                    if meta.get("number"):
                        doc_number = meta["number"]
                    if meta.get("title"):
                        doc_title = meta["title"]
                doc_copy["number"] = doc_number
                doc_copy["title"] = doc_title
                enriched_documents.append(doc_copy)

            canonical = max(enriched_documents, key=lambda item: len(str(item.get("number", ""))))
            current_ref = None
            versions = []
            for document in enriched_documents:
                source_id = str(document.get("id"))
                for version in document.get("versions", []):
                    try:
                        status = self.get_status(source_id, version.get("id"))
                    except StorageError:
                        continue
                    item = {
                        "document_id": source_id,
                        "version_id": version.get("id"),
                        "version_type": version.get("type"),
                        "status": version.get("status"),
                        "effective_from": version.get("effective_from"),
                        "change_number": status.get("change_number"),
                        "change_date": status.get("change_date"),
                        "filename": Path(version.get("file", "")).name,
                        "processing": status.get("processing", {}),
                    }
                    versions.append(item)
                    if version.get("status") == "current":
                        current_ref = (source_id, version)
            if current_ref is None:
                continue
            source_id, current_version = current_ref
            try:
                current = self.get_status(source_id, current_version.get("id"))
            except StorageError:
                continue
            versions.sort(key=lambda item: str(item.get("effective_from") or ""), reverse=True)
            current["number"] = canonical.get("number")
            current["title"] = canonical.get("title")
            current["versions"] = versions
            current["current_change_number"] = current.get("change_number")
            current["current_change_date"] = current.get("change_date") or current.get("effective_from")
            result.append(current)
        return sorted(result, key=lambda item: str(item.get("number") or ""))
