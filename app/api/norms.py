"""Project Expert AI — Norms API.

Provides the frontend with registered normative documents, PDF upload,
delete, and the existing full indexing pipeline.
"""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.api.schemas import NormDeleteResponse, NormIndexResponse, NormUploadResponse
from app.knowledge.build_sp_index import SPIndexBuilder
from app.knowledge.storage import KnowledgeStorage, StorageError


router = APIRouter(prefix="/api/norms", tags=["norms"])


def _safe_id(value: str) -> str:
    value = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", value).strip("._-")
    if not value:
        raise HTTPException(status_code=400, detail="Не удалось определить идентификатор документа")
    return value


def _normalize_filename(filename: str) -> str:
    return re.sub(r"[_-]+", " ", Path(filename).stem).strip()


def _infer_number(filename: str, supplied: str | None) -> str:
    if supplied and supplied.strip():
        return supplied.strip()

    normalized = _normalize_filename(filename)
    match = re.search(r"СП\s*[0-9]+(?:\.[0-9]+)+", normalized, re.IGNORECASE)
    if match:
        return re.sub(r"\s+", " ", match.group(0)).strip()
    return Path(filename).stem


def _find_existing_document_id(storage: KnowledgeStorage, number: str, filename: str) -> str | None:
    """Find a registry document represented by common SP filename variants."""
    normalized_number = re.sub(r"\s+", " ", number).strip().lower()
    normalized_filename = _normalize_filename(filename).lower()

    exact = []
    prefix = []
    for document in storage.registry.get_all_documents():
        doc_number = re.sub(r"\s+", " ", str(document.get("number", ""))).strip().lower()
        if doc_number == normalized_number:
            exact.append(document)
            continue
        if normalized_number and doc_number.startswith(normalized_number + "."):
            prefix.append(document)
        if str(document.get("id", "")).lower() in normalized_filename:
            prefix.append(document)

    matches = exact or prefix
    unique = {document.get("id"): document for document in matches if document.get("id")}
    if len(unique) == 1:
        return next(iter(unique))
    return None


def _find_duplicate_filename(storage: KnowledgeStorage, filename: str) -> tuple[str, str] | None:
    """Return document/version containing the same uploaded filename."""
    target = Path(filename).name.casefold()
    for document in storage.registry.get_all_documents():
        for version in document.get("versions", []):
            registered = version.get("file")
            if registered and Path(str(registered)).name.casefold() == target:
                return str(document.get("id", "")), str(version.get("id", ""))
    return None


def _index_norm(document_id: str, version_id: str) -> None:
    """Run the repository's existing complete SP pipeline and persist failures."""
    storage = KnowledgeStorage()
    paths = storage.paths(document_id, version_id)
    error_file = paths.index_root / "index_error.json"
    error_file.unlink(missing_ok=True)

    try:
        SPIndexBuilder(
            document_id=document_id,
            version_id=version_id,
            storage=storage,
        ).run()
    except Exception as error:
        storage.write_index_error(document_id, version_id, error)
        print(
            f"[Project Expert AI][Norms] Индексация завершилась ошибкой: "
            f"{document_id}/{version_id}: {error}"
        )


@router.get("")
def list_norms():
    storage = KnowledgeStorage()
    try:
        return {"documents": storage.list_statuses()}
    except StorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


# Static /upload MUST be declared before /{document_id}.
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

    storage = KnowledgeStorage()
    duplicate = _find_duplicate_filename(storage, filename)
    if duplicate:
        duplicate_document_id, duplicate_version_id = duplicate
        raise HTTPException(
            status_code=409,
            detail=(
                f"Данный документ уже загружен: {filename}. "
                f"Версия: {duplicate_document_id}/{duplicate_version_id}"
            ),
        )

    resolved_number = _infer_number(filename, number)
    resolved_document_id = _safe_id(document_id or resolved_number.replace(" ", "_"))

    existing_id = _find_existing_document_id(storage, resolved_number, filename)
    if existing_id:
        resolved_document_id = existing_id

    existing = storage.registry.get_document(resolved_document_id)

    if existing is not None and number and existing.get("number") != resolved_number:
        raise HTTPException(status_code=409, detail="Номер документа не совпадает с существующим Registry")

    if existing is not None:
        resolved_number = existing.get("number") or resolved_number

    resolved_title = (title or (existing.get("title") if existing else None) or resolved_number).strip()
    if existing is not None and title and existing.get("title") != resolved_title:
        raise HTTPException(status_code=409, detail="Название документа не совпадает с существующим Registry")
    if existing is not None:
        resolved_title = existing.get("title") or resolved_title

    if version_id:
        resolved_version_id = _safe_id(version_id)
    else:
        stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        resolved_version_id = _safe_id(f"{resolved_document_id}_{stamp}")

    resolved_effective_from = effective_from or date.today().isoformat()

    if existing is not None and any(
        v.get("id") == resolved_version_id for v in existing.get("versions", [])
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Версия уже существует: {resolved_document_id}/{resolved_version_id}",
        )

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
        storage.clear_index_error(document_id, version_id)
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


@router.delete("/{document_id}", response_model=NormDeleteResponse)
def delete_norm(document_id: str, version_id: str | None = None):
    """Удалить версию нормы и её производные файлы."""
    storage = KnowledgeStorage()
    try:
        version = storage.get_version(document_id, version_id)
        paths = storage.paths(document_id, version.get("id"))
        target_version_id = version.get("id")

        for path in (paths.pdf, paths.parsed, paths.structured):
            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                raise StorageError(f"Не удалось удалить файл {path}: {error}") from error

        if paths.index_root.exists():
            try:
                shutil.rmtree(paths.index_root)
            except OSError as error:
                raise StorageError(f"Не удалось удалить индекс {paths.index_root}: {error}") from error

        removed_version, document_removed = storage.registry.delete_version(
            document_id,
            target_version_id,
        )
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return NormDeleteResponse(
        success=True,
        document_id=document_id,
        version_id=target_version_id,
        document_removed=document_removed,
        message="Нормативный документ удалён" if document_removed else "Версия нормативного документа удалена",
    )


@router.get("/{document_id}")
def get_norm(document_id: str, version_id: str | None = None):
    storage = KnowledgeStorage()
    try:
        return storage.get_status(document_id, version_id)
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
