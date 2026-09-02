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
            if registered and storage.resolve(registered).exists() and _sha256_path(storage.resolve(registered)) == upload_hash:
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
        item["change_number"] = meta.get("change_number") if meta.get("change_number") is not None else item.get("change_number")
        item["change_date"] = meta.get("change_date") or item.get("change_date")
        item.setdefault("processing", {})
        item["processing"] = dict(item["processing"])
        item["processing"]["pages_count"] = meta.get("pages_count") or item["processing"].get("pages_count") or 0
        item["is_current"] = item.get("status") == "current"
        # Keep an explicit flag in the public payload so the frontend does not
        # have to reconstruct current-version state from registry internals.
        item["current_selected_by_user"] = bool(
            item.get("current_selected_by_user") is True or item["is_current"]
        )
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
    else:
        result["current_change_number"] = None
        result["current_change_date"] = None
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
        try:
            storage.refresh_version_metadata_from_parsed(document_id, version_id)
        except Exception as error:
            print(f"[Project Expert AI][Norms] Не удалось обновить метаданные версии: {document_id}/{version_id}: {error}")
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
