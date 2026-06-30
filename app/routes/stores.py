from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import StoreCreate, StoreOut
from app.services.gemini_file_search import GeminiFileSearchService


router = APIRouter()


@router.post("/stores", response_model=StoreOut)
def create_store(payload: StoreCreate) -> StoreOut:
    with get_db() as conn:
        existing = conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (payload.tenantId, payload.storeKey),
        ).fetchone()
        if existing:
            return _to_store_out(existing)

    try:
        gemini_store_name = GeminiFileSearchService().create_store(payload.displayName)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini store creation failed: {exc}") from exc

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO stores (tenant_id, store_key, display_name, gemini_store_name)
            VALUES (?, ?, ?, ?)
            """,
            (payload.tenantId, payload.storeKey, payload.displayName, gemini_store_name),
        )
        store = conn.execute("SELECT * FROM stores WHERE id = ?", (cursor.lastrowid,)).fetchone()

    return _to_store_out(store)


def _to_store_out(row: dict) -> StoreOut:
    return StoreOut(
        id=row["id"],
        tenantId=row["tenant_id"],
        storeKey=row["store_key"],
        displayName=row["display_name"],
        geminiStoreName=row["gemini_store_name"],
    )
