import hashlib
import shutil
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import get_db
from app.schemas import (
    DocumentListItem,
    DocumentListResponse,
    DocumentReplaceResponse,
    DocumentUpdateRequest,
    DocumentUploadResponse,
)
from app.security import require_internal_token
from app.services.gemini_file_search import GeminiFileSearchService


router = APIRouter(dependencies=[Depends(require_internal_token)])


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    tenantId: str | None = None,
    storeKey: str | None = None,
    status: str | None = None,
    active: Literal["true", "false", "all"] = "true",
) -> DocumentListResponse:
    where: list[str] = []
    params: list[object] = []
    if tenantId:
        where.append("s.tenant_id = ?")
        params.append(tenantId)
    if storeKey:
        where.append("s.store_key = ?")
        params.append(storeKey)
    if status:
        where.append("d.status = ?")
        params.append(status)
    if active != "all":
        where.append("d.active = ?")
        params.append(1 if active == "true" else 0)

    sql = """
        SELECT
            d.*,
            s.tenant_id,
            s.store_key,
            s.display_name
        FROM documents d
        JOIN stores s ON s.id = d.store_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY d.created_at DESC, d.id DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    items = [_to_document_list_item(row) for row in rows]
    return DocumentListResponse(items=items, count=len(items))


@router.post("/documents/upload", response_model=DocumentUploadResponse)
def upload_document(
    tenantId: str = Form(...),
    storeKey: str = Form(...),
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    store = _get_store(tenantId, storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    document, duplicate = _create_and_index_document(store, file)
    return _to_document_response(document, duplicate=duplicate)


@router.get("/documents/{document_id}", response_model=DocumentListItem)
def get_document(document_id: int) -> DocumentListItem:
    document = _get_document_details(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return _to_document_list_item(document)


@router.patch("/documents/{document_id}", response_model=DocumentListItem)
def update_document(
    document_id: int,
    payload: DocumentUpdateRequest,
) -> DocumentListItem:
    fields = payload.model_fields_set
    if not fields:
        raise HTTPException(status_code=400, detail="At least one field is required")
    if "active" in fields and payload.active is None:
        raise HTTPException(status_code=400, detail="active must be true or false")

    assignments: list[str] = []
    params: list[object] = []
    if "notes" in fields:
        notes = payload.notes.strip() if payload.notes else None
        assignments.append("notes = ?")
        params.append(notes)
    if "active" in fields:
        assignments.append("active = ?")
        params.append(1 if payload.active else 0)
        if payload.active:
            assignments.append("deleted_at = NULL")
        else:
            assignments.append("deleted_at = COALESCE(deleted_at, datetime('now'))")

    params.append(document_id)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        conn.execute(
            f"UPDATE documents SET {', '.join(assignments)} WHERE id = ?",
            params,
        )

    document = _get_document_details(document_id)
    return _to_document_list_item(document)


@router.delete("/documents/{document_id}")
def delete_document(document_id: int) -> dict[str, bool | int]:
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Document not found")
        conn.execute(
            """
            UPDATE documents
            SET active = 0,
                deleted_at = COALESCE(deleted_at, datetime('now'))
            WHERE id = ?
            """,
            (document_id,),
        )
    return {"deleted": True, "id": document_id, "active": False}


@router.post(
    "/documents/{document_id}/replace",
    response_model=DocumentReplaceResponse,
)
def replace_document(
    document_id: int,
    file: UploadFile = File(...),
) -> DocumentReplaceResponse:
    old_document = _get_document_details(document_id)
    if not old_document:
        raise HTTPException(status_code=404, detail="Document not found")

    store = {
        "id": old_document["store_id"],
        "gemini_store_name": old_document["gemini_store_name"],
    }
    new_document, _ = _create_and_index_document(
        store,
        file,
        reject_duplicate=True,
    )

    with get_db() as conn:
        conn.execute(
            """
            UPDATE documents
            SET active = 0,
                deleted_at = COALESCE(deleted_at, datetime('now')),
                replaced_by_document_id = ?
            WHERE id = ?
            """,
            (new_document["id"], document_id),
        )

    return DocumentReplaceResponse(
        replaced=True,
        oldDocumentId=document_id,
        newDocument=_to_document_response(new_document),
    )


def _create_and_index_document(
    store: dict,
    file: UploadFile,
    reject_duplicate: bool = False,
) -> tuple[dict, bool]:
    saved_path, sha256, size_bytes = _save_upload(store["id"], file)

    with get_db() as conn:
        duplicate = conn.execute(
            "SELECT * FROM documents WHERE store_id = ? AND sha256 = ?",
            (store["id"], sha256),
        ).fetchone()
        if duplicate:
            if Path(saved_path) != Path(duplicate["local_path"]):
                Path(saved_path).unlink(missing_ok=True)
            if reject_duplicate:
                raise HTTPException(
                    status_code=409,
                    detail="Replacement file is already registered in this store",
                )
            return duplicate, True

        cursor = conn.execute(
            """
            INSERT INTO documents (
                store_id, original_filename, local_path, sha256, mime_type, size_bytes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                store["id"],
                file.filename or "upload.bin",
                saved_path,
                sha256,
                file.content_type,
                size_bytes,
                "uploaded",
            ),
        )
        document_id = cursor.lastrowid

    try:
        document_name = GeminiFileSearchService().upload_and_wait(
            store["gemini_store_name"],
            saved_path,
            file.content_type,
        )
        with get_db() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'indexed',
                    gemini_document_name = ?,
                    indexed_at = datetime('now')
                WHERE id = ?
                """,
                (document_name, document_id),
            )
            document = conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return document, False
    except HTTPException:
        raise
    except Exception as exc:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = 'failed', error_message = ?
                WHERE id = ?
                """,
                (str(exc), document_id),
            )
        raise HTTPException(
            status_code=502,
            detail=f"Gemini document upload/indexing failed: {exc}",
        ) from exc


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
        ).fetchone()


def _get_document_details(document_id: int) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                d.*,
                s.tenant_id,
                s.store_key,
                s.display_name,
                s.gemini_store_name
            FROM documents d
            JOIN stores s ON s.id = d.store_id
            WHERE d.id = ?
            """,
            (document_id,),
        ).fetchone()


def _save_upload(store_id: int, upload: UploadFile) -> tuple[str, str, int]:
    upload_dir = Path(settings.upload_dir) / str(store_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "upload.bin").suffix
    temp_path = upload_dir / "incoming.tmp"

    sha = hashlib.sha256()
    size = 0
    with temp_path.open("wb") as out:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            sha.update(chunk)
            out.write(chunk)

    digest = sha.hexdigest()
    final_path = upload_dir / f"{digest}{suffix}"
    if temp_path != final_path:
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
        else:
            shutil.move(str(temp_path), str(final_path))
    return str(final_path), digest, size


def _to_document_response(
    row: dict,
    duplicate: bool = False,
) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        id=row["id"],
        storeId=row["store_id"],
        originalFilename=row["original_filename"],
        sha256=row["sha256"],
        status=row["status"],
        geminiDocumentName=row["gemini_document_name"],
        duplicate=duplicate,
    )


def _to_document_list_item(row: dict) -> DocumentListItem:
    return DocumentListItem(
        id=row["id"],
        storeId=row["store_id"],
        tenantId=row["tenant_id"],
        storeKey=row["store_key"],
        displayName=row["display_name"],
        originalFilename=row["original_filename"],
        sha256=row["sha256"],
        mimeType=row["mime_type"],
        sizeBytes=row["size_bytes"],
        geminiDocumentName=row["gemini_document_name"],
        status=row["status"],
        active=bool(row["active"]),
        notes=row["notes"],
        errorMessage=row["error_message"],
        createdAt=row["created_at"],
        indexedAt=row["indexed_at"],
        deletedAt=row["deleted_at"],
        replacedByDocumentId=row["replaced_by_document_id"],
    )
