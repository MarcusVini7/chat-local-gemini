from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import StoreCreate, StoreListItem, StoreListResponse, StoreOut
from app.services.gemini_file_search import GeminiFileSearchService


router = APIRouter()


@router.get("/stores", response_model=StoreListResponse)
def list_stores(
    tenantId: str | None = None,
    storeKey: str | None = None,
) -> StoreListResponse:
    where: list[str] = []
    params: list[str] = []
    if tenantId:
        where.append("tenant_id = ?")
        params.append(tenantId)
    if storeKey:
        where.append("store_key = ?")
        params.append(storeKey)

    sql = "SELECT * FROM stores"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    items = [_to_store_list_item(row) for row in rows]
    return StoreListResponse(items=items, count=len(items))


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


def _to_store_list_item(row: dict) -> StoreListItem:
    return StoreListItem(
        id=row["id"],
        tenantId=row["tenant_id"],
        storeKey=row["store_key"],
        displayName=row["display_name"],
        geminiStoreName=row["gemini_store_name"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )
