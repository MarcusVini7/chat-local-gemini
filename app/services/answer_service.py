import json

from app.database import get_db
from app.schemas import Citation, CustomerAnswerResponse, QueryResponse
from app.services.gemini_file_search import GeminiFileSearchService
from app.services.prompt_service import customer_prompt, customer_requested_human, query_prompt


INSUFFICIENT_MARKERS = [
    "nao ha informacao suficiente",
    "não há informação suficiente",
    "nao encontrei informacao",
    "não encontrei informação",
    "necessario verificar",
    "necessário verificar",
]


def answer_query(store: dict, question: str) -> QueryResponse:
    service = GeminiFileSearchService()
    answer, citations = service.answer_with_sources(
        store["gemini_store_name"],
        query_prompt(question),
    )
    confidence, reason = score_answer(answer, citations)
    _save_query(store["id"], None, question, answer, confidence, False, citations)
    return QueryResponse(answer=answer, citations=citations, confidence=confidence, reason=reason)


def answer_customer(store: dict, payload) -> CustomerAnswerResponse:
    requested_human = customer_requested_human(payload.customerMessage)
    if requested_human:
        answer = "Vou encaminhar sua solicitação para um atendente humano acompanhar essa situação."
        citations: list[Citation] = []
        confidence = "high"
        should_escalate = True
        reason = "customer_requested_human"
    else:
        service = GeminiFileSearchService()
        answer, citations = service.answer_with_sources(
            store["gemini_store_name"],
            customer_prompt(
                payload.customerMessage,
                payload.channel,
                payload.style,
                payload.ticketContext,
            ),
        )
        confidence, reason = score_answer(answer, citations)
        should_escalate = confidence == "low"

    _save_query(
        store["id"],
        payload.channel,
        payload.customerMessage,
        answer,
        confidence,
        should_escalate,
        citations,
    )
    return CustomerAnswerResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        shouldEscalate=should_escalate,
        reason=reason,
    )


def score_answer(answer: str, citations: list[Citation]) -> tuple[str, str]:
    lowered = answer.lower()
    if any(marker in lowered for marker in INSUFFICIENT_MARKERS):
        return "low", "insufficient_source_coverage"
    if citations:
        return "high", "answer_grounded_in_sources"
    if answer.strip():
        return "medium", "answer_without_explicit_citations"
    return "low", "empty_model_response"


def _save_query(
    store_id: int,
    channel: str | None,
    question: str,
    answer: str,
    confidence: str,
    should_escalate: bool,
    citations: list[Citation],
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO queries (
                store_id, channel, question, answer, confidence, should_escalate, citations_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                store_id,
                channel,
                question,
                answer,
                confidence,
                1 if should_escalate else 0,
                json.dumps([citation.model_dump() for citation in citations], ensure_ascii=False),
            ),
        )
