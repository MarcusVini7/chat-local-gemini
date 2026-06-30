from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas import CustomerAnswerRequest, CustomerAnswerResponse, QueryRequest, QueryResponse
from app.services.answer_service import answer_customer, answer_query


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return answer_query(store, payload.question)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini query failed: {exc}") from exc


@router.post("/answer/customer", response_model=CustomerAnswerResponse)
def answer_customer_route(payload: CustomerAnswerRequest) -> CustomerAnswerResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return answer_customer(store, payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini answer failed: {exc}") from exc


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
        ).fetchone()
