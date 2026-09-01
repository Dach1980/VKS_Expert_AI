"""Project Expert AI — Norms API v4."""
from __future__ import annotations

import hashlib
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.api.schemas import NormDeleteResponse, NormIndexResponse, NormUploadResponse
from app.knowledge.build_sp_index import SPIndexBuilder
from app.knowledge.norm_metadata import extract_version_metadata
from app.knowledge.registry_manager import RegistryError
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
    match = re.search(r"(?:СП|ГОСТ|ГОСТ Р|СНиП|ТР|ФЗ)\s*[0-9]+(?:\.[0-9]+)+", normalized, re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(0)).strip() if match else Path(filename).stem


def _number_group_key(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    match = re.search(r"(?:сп|гост(?: р)?|снип|тр|фз)\s*[0-9]+\.[0-9]+", normalized, re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(0)).strip() if match else normalized


def _find_existing_document_id(storage: KnowledgeStorage, number: str, filename: str) -> str | None:
    normalized_number = re.sub(r"\s+", " ", number).strip().lower()
    normalized_filename = _normalize_filename(filename).lower()
    target_group = _number_group_key(number)
    matches = []
    for document in storage.registry.get_all_documents():
        doc_id = str(document.get("id", ""))
        doc_number = re.sub(r"\s+", " ", str(document.get("number", ""))).strip().lower()
        if doc_number == normalized_number or (target_group and _number_group_key(doc_number) == target_group) or (normalized_number and doc_number.startswith(normalized_number + ".")) or (doc_id.lower().replace("_", " ") in normalized_filename):
            matches.append(document)
    if not matches:
        return None
    matches.sort(key=lambda d: (len(d.get("versions", [])), len(str(d.get("number", "")))), reverse=True)
    return str(matches[0].get("id"))


def _sha256_uploaded(upload_file: UploadFile) -> str:
    digest = hashlib.sha256()
    upload_file.file.seek(0)
    for chunk in iter(lambda: upload_file.file.read(1024 * 1024), b""):
        digest.update(chunk)
    upload_file.file.seek(0)
    return digest.hexdigest()


def _sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _find_duplicate_version(storage: KnowledgeStorage, upload_hash: str):
    for document in storage.registry.get_all_documents():
        for version in document.get("versions", []):
            registered = version.get("file")
            if registered and _sha256_path(storage.resolve(registered)) == upload_hash:
                return document, version
    root = storage.knowledge_root / "regulations"
    if root.exists():
        for path in root.rglob("*.pdf"):
            if _sha256_path(path) != upload_hash:
                continue
            for document in storage.registry.get_all_documents():
                for version in document.get("versions", []):
                    if storage.resolve(version.get("file", "")) == path:
                        return document, version
            return {"id": path.parent.name, "number": path.parent.name}, {"id": path.stem}
    return None


def _version_metadata(storage: KnowledgeStorage, document_id: str, version_id: str) -> dict:
    version = storage.get_version(document_id, version_id)
    return storage.get_version_metadata(document_id, version_id)


def _enrich_payload(storage: KnowledgeStorage, payload: dict) -> dict:
    versions = []
    current_meta = {}
    for source in payload.get("versions", []):
        source_id = str(source.get("document_id") or payload.get("document_id"))
        version_id = str(source.get("version_id") or source.get("id"))
        try:
            meta = _version_metadata(storage, source_id, version_id)
        except Exception:
            meta = {}
        item = dict(source)
        item["number"] = item.get("number") or meta.get("number") or payload.get("number")
        item["title"] = item.get("title") or meta.get("title") or payload.get("title")
        item["change_number"] = item.get("change_number") if item.get("change_number") is not None else meta.get("change_number")
        item["change_date"] = item.get("change_date") or meta.get("change_date")
        item.setdefault("processing", {})
        item["processing"] = dict(item["processing"])
        item["processing"]["pages_count"] = meta.get("pages_count") or item["processing"].get("pages_count") or 0
        item["is_current"] = item.get("status") == "current"
        item["original_filename"] = item.get("original_filename") or item.get("filename") or Path(item.get("file", "")).name
        versions.append(item)
        if item["is_current"]:
            current_meta = meta

    result = dict(payload)
    if current_meta:
        result["number"] = current_meta.get("number") or result.get("number")
        result["title"] = current_meta.get("title") or result.get("title")
        result["current_change_number"] = current_meta.get("change_number")
        result["current_change_date"] = current_meta.get("change_date") or result.get("effective_from")
        result.setdefault("processing", {})
        result["processing"] = dict(result["processing"])
        result["processing"]["pages_count"] = current_meta.get("pages_count") or result["processing"].get("pages_count") or 0
    result["versions"] = versions
    return result


def _index_norm(document_id: str, version_id: str) -> None:
    storage = KnowledgeStorage()
    paths = storage.paths(document_id, version_id)
    paths.index_root.mkdir(parents=True, exist_ok=True)
    paths.embeddings.mkdir(parents=True, exist_ok=True)
    storage.clear_index_error(document_id, version_id)
    storage.start_indexing(document_id, version_id)
    try:
        SPIndexBuilder(document_id=document_id, version_id=version_id, storage=storage).run()
    except Exception as error:
        storage.write_index_error(document_id, version_id, error)
        print(f"[Project Expert AI][Norms] Индексация завершилась ошибкой: {document_id}/{version_id}: {error}")
    finally:
        storage.finish_indexing(document_id, version_id)


@router.get("")
def list_norms():
    storage = KnowledgeStorage()
    try:
        return {"documents": [_enrich_payload(storage, d) for d in storage.list_statuses()]}
    except StorageError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/storage")
def get_norm_storage():
    storage = KnowledgeStorage()
    root = storage.get_vector_index_root()
    indexes = []
    if root.exists():
        for path in root.rglob("index.faiss"):
            indexes.append({"path": str(path), "size_bytes": path.stat().st_size})
    return {"backend": "FAISS", "path": str(root), "indexes": indexes}


@router.post("/storage/pick-folder")
def pick_norm_storage_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Tkinter недоступен: {error}") from error
    storage = KnowledgeStorage()
    initial = str(storage.get_vector_index_root())
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="Выберите папку для хранения векторных индексов Project Expert AI", initialdir=initial if Path(initial).exists() else str(Path.home()), mustexist=True)
    finally:
        root.destroy()
    if not selected:
        return {"selected": False, "path": initial}
    path = storage.set_vector_index_root(selected)
    return {"selected": True, "path": str(path), "backend": "FAISS"}


@router.post("/upload", response_model=NormUploadResponse)
def upload_norm(file: UploadFile = File(...), number: str | None = None, title: str | None = None, document_id: str | None = None, version_id: str | None = None, effective_from: str | None = None):
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Для нормативной базы поддерживается только PDF")
    storage = KnowledgeStorage()
    upload_hash = _sha256_uploaded(file)
    duplicate = _find_duplicate_version(storage, upload_hash)
    if duplicate:
        document, version = duplicate
        original = version.get("original_filename") or Path(version.get("file", "")).name or version.get("id")
        raise HTTPException(status_code=409, detail=f"Данный файл уже загружен: «{original}». Документ: {document.get('number', document.get('id'))}. Версия: {version.get('id')}.")

    resolved_number = _infer_number(filename, number)
    resolved_document_id = _safe_id(document_id or resolved_number.replace(" ", "_"))
    existing_id = _find_existing_document_id(storage, resolved_number, filename)
    if existing_id:
        resolved_document_id = existing_id
    existing = storage.registry.get_document(resolved_document_id)
    resolved_title = (title or (existing.get("title") if existing else None) or "Внутренний водопровод и канализация зданий").strip()
    resolved_version_id = _safe_id(version_id) if version_id else _safe_id(f"{resolved_document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    resolved_effective_from = effective_from or date.today().isoformat()
    relative_dir = Path("knowledge") / "regulations" / resolved_document_id
    relative_pdf = relative_dir / f"{resolved_version_id}.pdf"
    relative_parsed = Path("knowledge") / "parsed" / f"{resolved_version_id}.json"
    relative_structured = Path("knowledge") / "structured" / f"{resolved_version_id}.json"
    try:
        storage.registry.register_version(document_id=resolved_document_id, number=resolved_number, title=resolved_title, version_id=resolved_version_id, version_type="edition", effective_from=resolved_effective_from, file_path=str(relative_pdf).replace("\\", "/"), parsed_file=str(relative_parsed).replace("\\", "/"), structured_file=str(relative_structured).replace("\\", "/"), make_current=False)
        saved = storage.save_uploaded_pdf(resolved_document_id, file, resolved_version_id)
        filename_meta = storage._classify_uploaded_filename(filename)
        meta = extract_version_metadata(saved, storage.resolve(relative_parsed))
        document = storage.registry.get_document(resolved_document_id)
        version = next(v for v in document.get("versions", []) if v.get("id") == resolved_version_id)

        if meta.get("number"):
            document["number"] = meta["number"]
        if meta.get("title"):
            document["title"] = meta["title"]

        # Only an explicit filename may classify a newly uploaded file as base
        # or amendment. Otherwise the change number is deliberately left unset;
        # the authoritative number can later come from that version's parsed JSON.
        version_type, filename_change = filename_meta
        if version_type == "base":
            version["type"] = "base"
            version.pop("change_number", None)
            version.pop("change_date", None)
        elif version_type == "amendment":
            version["type"] = "amendment"
            version["change_number"] = filename_change
        else:
            version["type"] = "edition"
            version.pop("change_number", None)
            version.pop("change_date", None)

        # Do not infer a change number from the PDF's visible text during upload:
        # the same base PDF can mention later amendments. Parsed JSON belonging to
        # this exact version is authoritative when it exists.
        if version_type != "base" and not filename_change:
            parsed_change = meta.get("change_number") if storage.resolve(relative_parsed).exists() else None
            if parsed_change:
                version["change_number"] = str(parsed_change)
                version["type"] = "amendment"
            parsed_date = meta.get("change_date") if storage.resolve(relative_parsed).exists() else None
            if parsed_date:
                version["change_date"] = str(parsed_date)
                if not effective_from:
                    version["effective_from"] = str(parsed_date)

        version["pages_count"] = int(meta.get("pages_count") or 0)
        version["sha256"] = upload_hash
        version["original_filename"] = filename
        storage.registry.save()
    except (StorageError, OSError, StopIteration, RegistryError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return NormUploadResponse(success=True, document_id=resolved_document_id, version_id=resolved_version_id, number=meta.get("number") or resolved_number, title=meta.get("title") or resolved_title, status="uploaded", filename=filename)


@router.post("/{document_id}/{version_id}/activate", response_model=NormIndexResponse)
def activate_norm_version(document_id: str, version_id: str):
    storage = KnowledgeStorage()
    try:
        target = storage.registry.activate_version(document_id, version_id)
    except RegistryError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return NormIndexResponse(success=True, document_id=document_id, version_id=version_id, status="current", message=f"Версия {target.get('id')} назначена действующей")


@router.post("/{document_id}/{version_id}/index", response_model=NormIndexResponse)
def index_norm(document_id: str, version_id: str, background_tasks: BackgroundTasks):
    storage = KnowledgeStorage()
    try:
        storage.get_version(document_id, version_id)
        paths = storage.paths(document_id, version_id)
        if not paths.pdf.exists():
            raise StorageError(f"PDF не найден: {paths.pdf}")
        storage.clear_index_error(document_id, version_id)
        storage.ensure_version_dirs(document_id, version_id)
        storage.start_indexing(document_id, version_id)
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    background_tasks.add_task(_index_norm_after_start, document_id, version_id)
    return NormIndexResponse(success=True, document_id=document_id, version_id=version_id, status="indexing", message="Индексация выбранной версии запущена")


def _index_norm_after_start(document_id: str, version_id: str) -> None:
    storage = KnowledgeStorage()
    try:
        SPIndexBuilder(document_id=document_id, version_id=version_id, storage=storage).run()
    except Exception as error:
        storage.write_index_error(document_id, version_id, error)
        print(f"[Project Expert AI][Norms] Индексация завершилась ошибкой: {document_id}/{version_id}: {error}")
    finally:
        storage.finish_indexing(document_id, version_id)


@router.delete("/{document_id}", response_model=NormDeleteResponse)
def delete_norm(document_id: str, version_id: str | None = None):
    storage = KnowledgeStorage()
    try:
        if version_id is None:
            raise StorageError("Не указана версия для удаления")
        version = storage.get_version(document_id, version_id)
        paths = storage.paths(document_id, version.get("id"))
        target_version_id = version.get("id")
        for path in (paths.pdf, paths.parsed, paths.structured):
            path.unlink(missing_ok=True)
        if paths.index_root.exists():
            shutil.rmtree(paths.index_root)
        _, document_removed = storage.registry.delete_version(document_id, target_version_id)
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return NormDeleteResponse(success=True, document_id=document_id, version_id=target_version_id, document_removed=document_removed, message="Нормативный документ удалён" if document_removed else "Нормативная версия удалена")


@router.get("/{document_id}")
def get_norm(document_id: str, version_id: str | None = None):
    storage = KnowledgeStorage()
    try:
        status = storage.get_status(document_id, version_id)
        document = storage.registry.get_document(document_id)
        status["versions"] = []
        for version in document.get("versions", []):
            version_status = storage.get_status(document_id, version.get("id"))
            status["versions"].append({
                "document_id": document_id,
                "version_id": version.get("id"),
                "version_type": version.get("type"),
                "status": version.get("status"),
                "effective_from": version.get("effective_from"),
                "change_number": version_status.get("change_number"),
                "change_date": version_status.get("change_date"),
                "filename": version.get("original_filename") or Path(version.get("file", "")).name,
                "processing": version_status.get("processing", {}),
            })
        return status
    except StorageError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
