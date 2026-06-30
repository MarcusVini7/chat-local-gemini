import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam

from app.database import get_db
from app.schemas import (
    Citation,
    CustomerAnswerRequest,
    CustomerAnswerResponse,
    QueryListItem,
    QueryListResponse,
    QueryRequest,
    QueryResponse,
)
from app.security import require_internal_token
from app.services.answer_service import answer_customer, answer_query


router = APIRouter(dependencies=[Depends(require_internal_token)])


@router.get("/queries", response_model=QueryListResponse)
def list_queries(
    tenantId: str | None = None,
    storeKey: str | None = None,
    channel: str | None = None,
    confidence: str | None = None,
    shouldEscalate: bool | None = None,
    limit: int = QueryParam(default=50, ge=1, le=200),
) -> QueryListResponse:
    where: list[str] = []
    params: list[object] = []
    if tenantId:
        where.append("s.tenant_id = ?")
        params.append(tenantId)
    if storeKey:
        where.append("s.store_key = ?")
        params.append(storeKey)
    if channel:
        where.append("q.channel = ?")
        params.append(channel)
    if confidence:
        where.append("q.confidence = ?")
        params.append(confidence)
    if shouldEscalate is not None:
        where.append("q.should_escalate = ?")
        params.append(1 if shouldEscalate else 0)

    sql = """
        SELECT
            q.*,
            s.tenant_id,
            s.store_key
        FROM queries q
        JOIN stores s ON s.id = q.store_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY q.created_at DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        citation_names = _load_citation_names(conn, rows)

    items = [_to_query_list_item(row, citation_names) for row in rows]
    return QueryListResponse(items=items, count=len(items))


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


def _load_citation_names(conn, rows: list[dict]) -> dict[tuple[int, str], str]:
    store_ids = sorted({row["store_id"] for row in rows})
    if not store_ids:
        return {}

    placeholders = ",".join("?" for _ in store_ids)
    doc_rows = conn.execute(
        f"""
        SELECT store_id, sha256, original_filename
        FROM documents
        WHERE store_id IN ({placeholders})
        """,
        store_ids,
    ).fetchall()
    return {
        (row["store_id"], row["sha256"]): row["original_filename"]
        for row in doc_rows
    }


def _to_query_list_item(row: dict, citation_names: dict[tuple[int, str], str]) -> QueryListItem:
    return QueryListItem(
        id=row["id"],
        storeId=row["store_id"],
        tenantId=row["tenant_id"],
        storeKey=row["store_key"],
        channel=row["channel"],
        question=row["question"],
        answer=row["answer"],
        confidence=row["confidence"],
        shouldEscalate=bool(row["should_escalate"]),
        citations=_parse_citations(row["citations_json"], row["store_id"], citation_names),
        createdAt=row["created_at"],
    )


def _parse_citations(
    raw: str | None,
    store_id: int,
    citation_names: dict[tuple[int, str], str],
) -> list[Citation]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []

    citations: list[Citation] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        if not source:
            continue
        page = item.get("page")
        snippet = item.get("snippet")
        citations.append(
            Citation(
                source=_normalize_source(str(source), store_id, citation_names),
                page=page if isinstance(page, int) else None,
                snippet=snippet if isinstance(snippet, str) else None,
            )
        )
    return citations


def _normalize_source(
    source: str,
    store_id: int,
    citation_names: dict[tuple[int, str], str],
) -> str:
    match = re.search(r"([a-f0-9]{64})", source, re.IGNORECASE)
    if not match:
        return source
    return citation_names.get((store_id, match.group(1).lower()), source)
