"""VKS Expert AI — Norms API.

Provides the frontend with registered normative documents, PDF upload,
and the existing full indexing pipeline.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.api.schemas import NormIndexResponse, NormUploadResponse
from app.knowledge.build_sp_index import SPIndexBuilder
from app.knowledge.storage import KnowledgeStorage, StorageError


router = APIRouter(prefix="/api/norms", tags=["norms"])


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", value).strip("._-")
    if not value:
        raise HTTPException(status_code=400, detail="Не удалось определить идентификатор документа")
    return value


def _infer_number(filename: str, supplied: str | None) -> str:
    if supplied and supplied.strip():
        return supplied.strip()
    match = re.search(r"СП\s*[0-9]+(?:\.[0-9]+)+", filename, re.IGNORECASE)
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip()
    return Path(filename).stem


def _index_norm(document_id: str, version_id: str) -> None:
    """Background task: run the repository's existing complete SP pipeline."""
    SPIndexBuilder(document_id=document_id, version_id=version_id).run()


@router.get("")
def list_norms():
    storage = KnowledgeStorage()
    try:
        return {"documents": storage.list_statuses()}
    except StorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/{document_id}")
def get_norm(document_id: str, version_id: str | None = None):
    storage = KnowledgeStorage()
    try:
        return storage.get_status(document_id, version_id)
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/upload", response_model=NormUploadResponse)
def upload_norm(
    file: UploadFile = File(...),
    number: str | None = None,
    title: str | None = None,
    document_id: str | None = None,
    version_id: str | None = None,
    effective_from: str | None = None,
):
    """Загрузить PDF в Registry/Storage как новую версию."""
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Для нормативной базы поддерживается только PDF")

    resolved_number = _infer_number(filename, number)
    resolved_document_id = _safe_id(
        document_id or resolved_number.replace(" ", "_")
    )
    storage = KnowledgeStorage()
    existing = storage.registry.get_document(resolved_document_id)

    if existing is not None and existing.get("number") != resolved_number:
        raise HTTPException(status_code=409, detail="Номер документа не совпадает с существующим Registry")

    resolved_title = (title or (existing.get("title") if existing else None) or resolved_number).strip()
    resolved_version_id = _safe_id(
        version_id or f"{resolved_document_id}_{date.today().isoformat().replace('-', '')}"
    )
    resolved_effective_from = effective_from or date.today().isoformat()

    if existing is not None and any(v.get("id") == resolved_version_id for v in existing.get("versions", [])):
        raise HTTPException(status_code=409, detail=f"Версия уже существует: {resolved_document_id}/{resolved_version_id}")

    relative_dir = Path("knowledge") / "regulations" / resolved_document_id
    relative_pdf = relative_dir / f"{resolved_version_id}.pdf"
    relative_parsed = Path("knowledge") / "parsed" / f"{resolved_version_id}.json"
    relative_structured = Path("knowledge") / "structured" / f"{resolved_version_id}.json"

    try:
        storage.registry.register_version(
            document_id=resolved_document_id,
            number=resolved_number,
            title=resolved_title,
            version_id=resolved_version_id,
            version_type="edition",
            effective_from=resolved_effective_from,
            file_path=str(relative_pdf).replace("\\", "/"),
            parsed_file=str(relative_parsed).replace("\\", "/"),
            structured_file=str(relative_structured).replace("\\", "/"),
            make_current=False,
        )
        saved = storage.save_uploaded_pdf(resolved_document_id, file, resolved_version_id)
        storage.registry.activate_version(resolved_document_id, resolved_version_id)
    except StorageError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return NormUploadResponse(
        success=True,
        document_id=resolved_document_id,
        version_id=resolved_version_id,
        number=resolved_number,
        title=resolved_title,
        status="current",
        filename=saved.name,
    )


@router.post("/{document_id}/{version_id}/index", response_model=NormIndexResponse)
def index_norm(document_id: str, version_id: str, background_tasks: BackgroundTasks):
    """Запустить существующий полный SPIndexBuilder в фоне."""
    storage = KnowledgeStorage()
    try:
        storage.get_version(document_id, version_id)
        paths = storage.paths(document_id, version_id)
        if not paths.pdf.exists():
            raise StorageError(f"PDF не найден: {paths.pdf}")
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    background_tasks.add_task(_index_norm, document_id, version_id)
    return NormIndexResponse(
        success=True,
        document_id=document_id,
        version_id=version_id,
        status="indexing",
        message="Полная индексация запущена",
    )
