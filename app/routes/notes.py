from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.schemas import (
    NoteCreateRequest,
    NoteResponse,
    NotesListResponse,
    NoteUpdateRequest,
)
from app.security import require_internal_token


router = APIRouter(dependencies=[Depends(require_internal_token)])


@router.get("/notes", response_model=NotesListResponse)
def list_notes(tenantId: str, storeKey: str) -> NotesListResponse:
    store = _get_store(tenantId, storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT n.*, s.tenant_id, s.store_key
            FROM notes n
            JOIN stores s ON s.id = n.store_id
            WHERE n.store_id = ?
            ORDER BY n.updated_at DESC, n.id DESC
            """,
            (store["id"],),
        ).fetchall()

    items = [_to_note_response(row) for row in rows]
    return NotesListResponse(items=items, count=len(items))


@router.post("/notes", response_model=NoteResponse)
def create_note(payload: NoteCreateRequest) -> NoteResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if payload.sourceQueryId is not None:
        _validate_source_query(store["id"], payload.sourceQueryId)

    title = payload.title.strip()
    content = payload.content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content cannot be empty")

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO notes (
                store_id, title, content, source_type, source_query_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                store["id"],
                title,
                content,
                payload.sourceType,
                payload.sourceQueryId,
            ),
        )
        row = _get_note_row(conn, cursor.lastrowid)

    return _to_note_response(row)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, payload: NoteUpdateRequest) -> NoteResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates or any(value is None for value in updates.values()):
        raise HTTPException(status_code=400, detail="At least one non-empty field is required")

    assignments: list[str] = []
    params: list[object] = []
    for field in ("title", "content"):
        if field in updates:
            value = updates[field].strip()
            if not value:
                raise HTTPException(status_code=400, detail=f"{field} cannot be empty")
            assignments.append(f"{field} = ?")
            params.append(value)

    assignments.append("updated_at = datetime('now')")
    params.append(note_id)

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found")
        conn.execute(
            f"UPDATE notes SET {', '.join(assignments)} WHERE id = ?",
            params,
        )
        row = _get_note_row(conn, note_id)

    return _to_note_response(row)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int) -> dict[str, bool | int]:
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found")
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    return {"deleted": True, "id": note_id}


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
        ).fetchone()


def _validate_source_query(store_id: int, query_id: int) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM queries WHERE id = ? AND store_id = ?",
            (query_id, store_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Source query does not belong to store")


def _get_note_row(conn, note_id: int) -> dict:
    return conn.execute(
        """
        SELECT n.*, s.tenant_id, s.store_key
        FROM notes n
        JOIN stores s ON s.id = n.store_id
        WHERE n.id = ?
        """,
        (note_id,),
    ).fetchone()


def _to_note_response(row: dict) -> NoteResponse:
    return NoteResponse(
        id=row["id"],
        storeId=row["store_id"],
        tenantId=row["tenant_id"],
        storeKey=row["store_key"],
        title=row["title"],
        content=row["content"],
        sourceType=row["source_type"],
        sourceQueryId=row["source_query_id"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )
