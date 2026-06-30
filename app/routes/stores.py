import re

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.schemas import (
    StoreCreate,
    StoreListItem,
    StoreListResponse,
    StoreDocumentStats,
    StoreNoteStats,
    StoreOut,
    StoreQueryStats,
    StoreSummaryRequest,
    StoreSummaryResponse,
    StoreStatsResponse,
    SuggestQuestionsRequest,
    SuggestQuestionsResponse,
)
from app.security import require_internal_token
from app.services.answer_service import answer_store_prompt
from app.services.gemini_file_search import GeminiFileSearchService
from app.services.prompt_service import store_summary_prompt, suggested_questions_prompt


router = APIRouter(dependencies=[Depends(require_internal_token)])


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


@router.get("/stores/stats", response_model=StoreStatsResponse)
def store_stats(tenantId: str, storeKey: str) -> StoreStatsResponse:
    store = _get_store(tenantId, storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    with get_db() as conn:
        document_stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN active = 0 THEN 1 ELSE 0 END) AS inactive,
                SUM(CASE WHEN status = 'indexed' THEN 1 ELSE 0 END) AS indexed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) AS uploaded
            FROM documents
            WHERE store_id = ?
            """,
            (store["id"],),
        ).fetchone()
        query_stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN confidence = 'high' THEN 1 ELSE 0 END) AS high_confidence,
                SUM(CASE WHEN confidence = 'low' THEN 1 ELSE 0 END) AS low_confidence,
                SUM(CASE WHEN should_escalate = 1 THEN 1 ELSE 0 END) AS should_escalate
            FROM queries
            WHERE store_id = ?
            """,
            (store["id"],),
        ).fetchone()
        note_stats = conn.execute(
            "SELECT COUNT(*) AS total FROM notes WHERE store_id = ?",
            (store["id"],),
        ).fetchone()

    return StoreStatsResponse(
        tenantId=store["tenant_id"],
        storeKey=store["store_key"],
        displayName=store["display_name"],
        documents=StoreDocumentStats(
            total=document_stats["total"] or 0,
            active=document_stats["active"] or 0,
            inactive=document_stats["inactive"] or 0,
            indexed=document_stats["indexed"] or 0,
            failed=document_stats["failed"] or 0,
            uploaded=document_stats["uploaded"] or 0,
        ),
        queries=StoreQueryStats(
            total=query_stats["total"] or 0,
            highConfidence=query_stats["high_confidence"] or 0,
            lowConfidence=query_stats["low_confidence"] or 0,
            shouldEscalate=query_stats["should_escalate"] or 0,
        ),
        notes=StoreNoteStats(total=note_stats["total"] or 0),
    )


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


@router.post("/stores/summary", response_model=StoreSummaryResponse)
def summarize_store(payload: StoreSummaryRequest) -> StoreSummaryResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        response = answer_store_prompt(store, store_summary_prompt())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini summary failed: {exc}") from exc
    return StoreSummaryResponse(
        summary=response.answer,
        citations=response.citations,
        confidence=response.confidence,
        reason=response.reason,
    )


@router.post("/stores/suggest-questions", response_model=SuggestQuestionsResponse)
def suggest_questions(payload: SuggestQuestionsRequest) -> SuggestQuestionsResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        response = answer_store_prompt(store, suggested_questions_prompt())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini question suggestion failed: {exc}") from exc
    return SuggestQuestionsResponse(
        questions=_parse_questions(response.answer),
        citations=response.citations,
        confidence=response.confidence,
        reason=response.reason,
    )


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
        ).fetchone()


def _parse_questions(answer: str) -> list[str]:
    questions: list[str] = []
    seen: set[str] = set()
    for raw_line in answer.splitlines():
        line = re.sub(r"^\s*(?:[-*•#]+|\d+[\.\)])\s*", "", raw_line).strip()
        line = line.strip('"').replace("**", "")
        if (
            not line
            or "?" not in line
            or line.lower().rstrip(":") in {"perguntas", "perguntas sugeridas"}
        ):
            continue
        normalized = line.casefold()
        if normalized not in seen:
            seen.add(normalized)
            questions.append(line)
        if len(questions) == 8:
            break
    return questions


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
