import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.database import get_db
from app.schemas import DocumentUploadResponse
from app.services.gemini_file_search import GeminiFileSearchService


router = APIRouter()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
def upload_document(
    tenantId: str = Form(...),
    storeKey: str = Form(...),
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    store = _get_store(tenantId, storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    saved_path, sha256, size_bytes = _save_upload(store["id"], file)

    with get_db() as conn:
        duplicate = conn.execute(
            "SELECT * FROM documents WHERE store_id = ? AND sha256 = ?",
            (store["id"], sha256),
        ).fetchone()
        if duplicate:
            Path(saved_path).unlink(missing_ok=True)
            return _to_document_response(duplicate, duplicate=True)

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
            document = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return _to_document_response(document)
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
            document = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        raise HTTPException(status_code=502, detail=f"Gemini document upload/indexing failed: {exc}") from exc


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
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


def _to_document_response(row: dict, duplicate: bool = False) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        id=row["id"],
        storeId=row["store_id"],
        originalFilename=row["original_filename"],
        sha256=row["sha256"],
        status=row["status"],
        geminiDocumentName=row["gemini_document_name"],
        duplicate=duplicate,
    )
