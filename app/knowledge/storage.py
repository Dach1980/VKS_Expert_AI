"""
VKS Expert AI
KnowledgeStorage v1

Единая точка доступа к хранилищу нормативных документов.

Storage отвечает только за расположение файлов и каталогов.
Сведения о документах и версиях берутся из DocumentRegistry.

Текущая структура сохраняется:

knowledge/
├── regulations/<document_id>/       PDF
├── parsed/                          parsed JSON
├── structured/                      structured JSON
└── index/<document_id>/
    ├── pages/
    ├── enriched/
    ├── document_chunks/
    └── embeddings/

Никаких абсолютных путей к проекту в pipeline-модулях.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.registry_manager import DocumentRegistry, RegistryError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"


class StorageError(Exception):
    """Ошибка работы с KnowledgeStorage."""


@dataclass(frozen=True)
class DocumentPaths:
    """Канонические пути одной версии нормативного документа."""

    pdf: Path
    parsed: Path
    structured: Path
    index_root: Path
    pages: Path
    enriched: Path
    chunks: Path
    embeddings: Path


class KnowledgeStorage:
    """
    Единый механизм расположения нормативных данных.

    Storage не хранит собственную копию реестра: RegistryManager
    остаётся источником истины для document_id и version_id.
    """

    def __init__(
        self,
        project_root: Path | str = PROJECT_ROOT,
        registry: DocumentRegistry | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.knowledge_root = self.project_root / "knowledge"
        self.registry = registry or DocumentRegistry(
            self.knowledge_root / "registry" / "documents.json",
            project_root=self.project_root,
        )

    # ---------------------------------------------------------
    # Registry
    # ---------------------------------------------------------

    def get_document(self, document_id: str) -> dict[str, Any]:
        document = self.registry.get_document(document_id)
        if document is None:
            raise StorageError(f"Документ не найден: {document_id}")
        return document

    def get_current_version(self, document_id: str) -> dict[str, Any]:
        try:
            return self.registry.get_current_version(document_id)
        except RegistryError as error:
            raise StorageError(str(error)) from error

    # ---------------------------------------------------------
    # Path resolution
    # ---------------------------------------------------------

    def resolve(self, relative_path: str | Path) -> Path:
        """Преобразует путь из registry в абсолютный путь проекта."""
        path = Path(relative_path)
        if path.is_absolute():
            return path
        return self.project_root / path

    def _version_path(
        self,
        document_id: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> Path | None:
        document = self.get_document(document_id)
        version = (
            next(
                (
                    item
                    for item in document.get("versions", [])
                    if item.get("id") == version_id
                ),
                None,
            )
            if version_id
            else self.get_current_version(document_id)
        )

        if version is None:
            raise StorageError(
                f"Версия {version_id!r} не найдена для {document_id}"
            )

        value = version.get(key)
        return self.resolve(value) if value else None

    def paths(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> DocumentPaths:
        """Возвращает полный набор канонических путей версии."""
        document = self.get_document(document_id)
        version = (
            next(
                (
                    item
                    for item in document.get("versions", [])
                    if item.get("id") == version_id
                ),
                None,
            )
            if version_id
            else self.get_current_version(document_id)
        )

        if version is None:
            raise StorageError(
                f"Версия {version_id!r} не найдена для {document_id}"
            )

        index_root = self.knowledge_root / "index" / document_id

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

    # ---------------------------------------------------------
    # Directory lifecycle
    # ---------------------------------------------------------

    def ensure_version_dirs(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> DocumentPaths:
        paths = self.paths(document_id, version_id)

        for directory in (
            paths.pages,
            paths.enriched,
            paths.chunks,
            paths.embeddings,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        paths.parsed.parent.mkdir(parents=True, exist_ok=True)
        paths.structured.parent.mkdir(parents=True, exist_ok=True)
        paths.pdf.parent.mkdir(parents=True, exist_ok=True)

        return paths

    # ---------------------------------------------------------
    # Upload
    # ---------------------------------------------------------

    def save_pdf(
        self,
        document_id: str,
        source: Path | str,
        version_id: str | None = None,
    ) -> Path:
        """Копирует PDF в зарегистрированное место хранения."""
        source_path = Path(source)
        if not source_path.exists():
            raise StorageError(f"Исходный PDF не найден: {source_path}")

        if source_path.suffix.lower() != ".pdf":
            raise StorageError("KnowledgeStorage принимает только PDF")

        paths = self.ensure_version_dirs(document_id, version_id)
        shutil.copy2(source_path, paths.pdf)
        return paths.pdf

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    def get_status(
        self,
        document_id: str,
        version_id: str | None = None,
    ) -> dict[str, Any]:
        """Возвращает технический статус обработки версии."""
        document = self.get_document(document_id)
        version = (
            next(
                (
                    item
                    for item in document.get("versions", [])
                    if item.get("id") == version_id
                ),
                None,
            )
            if version_id
            else self.get_current_version(document_id)
        )

        if version is None:
            raise StorageError(
                f"Версия {version_id!r} не найдена для {document_id}"
            )

        paths = self.paths(document_id, version.get("id"))
        page_files = list(paths.pages.glob("page_*.json")) if paths.pages.exists() else []
        enriched_files = list(paths.enriched.glob("page_*_enriched.json")) if paths.enriched.exists() else []
        chunks_file = paths.chunks / "all_chunks.json"
        embeddings_file = paths.embeddings / "index.faiss"
        metadata_file = paths.embeddings / "metadata.json"

        return {
            "document_id": document_id,
            "number": document.get("number"),
            "title": document.get("title"),
            "version_id": version.get("id"),
            "version_type": version.get("type"),
            "status": version.get("status"),
            "effective_from": version.get("effective_from"),
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
                "pages_indexed": len(page_files) > 0,
                "pages_count": len(page_files),
                "enriched": len(enriched_files) > 0,
                "enriched_pages_count": len(enriched_files),
                "chunks": chunks_file.exists(),
                "vector_index": embeddings_file.exists(),
                "vector_metadata": metadata_file.exists(),
            },
            "checked_at": datetime.now().isoformat(),
        }

    def list_statuses(self) -> list[dict[str, Any]]:
        return [
            self.get_status(document["id"])
            for document in self.registry.get_all_documents()
        ]
