import json
import unicodedata
from pathlib import Path

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
    "não tenho essa informação",
    "nao tenho essa informacao",
]

SENSITIVE_ACCESS_TERMS = [
    "senha",
    "password",
    "token",
    "api key",
    "chave api",
    "chave de api",
    "chave privada",
    "private key",
    "credencial",
    "credenciais",
    "secret",
    "segredo",
    "jwt_secret",
    "access token",
    "ssh key",
]

SENSITIVE_INFRA_TERMS = [
    "root",
    "ssh",
    "admin",
    "administrador",
    "servidor de producao",
    "servidor de produção",
    "producao",
    "produção",
    "banco de dados",
    "database",
]

REQUEST_ACTION_TERMS = [
    "qual",
    "quais",
    "me passa",
    "passa",
    "enviar",
    "envia",
    "informa",
    "informar",
    "mostrar",
    "mostra",
    "preciso",
    "quero",
    "acessar",
    "acesso",
    "login",
    "logar",
]


def answer_query(store: dict, question: str) -> QueryResponse:
    service = GeminiFileSearchService()
    answer, citations = service.answer_with_sources(
        store["gemini_store_name"],
        query_prompt(question),
    )
    citations = _normalize_citations(store["id"], citations)
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

    elif is_sensitive_access_request(payload.customerMessage):
        answer = _sensitive_access_answer(payload.channel)
        citations = []
        confidence = "low"
        should_escalate = True
        reason = "sensitive_access_request"

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
        citations = _normalize_citations(store["id"], citations)
        confidence, reason = score_answer(answer, citations)

        if not citations:
            answer = _no_grounded_source_answer(payload.channel)
            confidence = "low"
            should_escalate = True
            reason = "no_grounded_source"
        else:
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


def is_sensitive_access_request(message: str) -> bool:
    normalized = _normalize_text(message)

    if any(term in normalized for term in SENSITIVE_ACCESS_TERMS):
        return True

    has_infra_term = any(term in normalized for term in SENSITIVE_INFRA_TERMS)
    has_request_action = any(term in normalized for term in REQUEST_ACTION_TERMS)

    return has_infra_term and has_request_action


def _sensitive_access_answer(channel: str) -> str:
    if channel == "email":
        return (
            "Não posso informar senhas, tokens, chaves ou credenciais por este canal. "
            "Essa situação precisa ser tratada por um responsável autorizado da equipe técnica."
        )

    return (
        "Não consigo passar senha, token, chave ou credenciais por aqui. "
        "Essa situação precisa ser tratada por um responsável autorizado da equipe técnica."
    )


def _no_grounded_source_answer(channel: str) -> str:
    if channel == "email":
        return (
            "Não encontrei essa informação nas fontes disponíveis. "
            "Para evitar uma orientação incorreta, essa situação precisa ser analisada por um responsável."
        )

    return (
        "Não encontrei essa informação nas fontes disponíveis. "
        "Para não te passar uma orientação incorreta, vou marcar essa situação para análise de um responsável."
    )


def _normalize_citations(store_id: int, citations: list[Citation]) -> list[Citation]:
    if not citations:
        return []

    docs = _load_documents_for_store(store_id)
    normalized: list[Citation] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    for citation in citations:
        mapped_source = _map_citation_source(citation.source, docs)
        item = Citation(
            source=mapped_source,
            page=citation.page,
            snippet=citation.snippet,
        )
        key = (item.source, str(item.page) if item.page is not None else None, item.snippet)
        if key not in seen:
            seen.add(key)
            normalized.append(item)

    return normalized


def _load_documents_for_store(store_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT original_filename, local_path, sha256, gemini_document_name
            FROM documents
            WHERE store_id = ?
            """,
            (store_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def _map_citation_source(source: str, docs: list[dict]) -> str:
    if not source:
        return source

    source_name = Path(source).name

    for doc in docs:
        original = doc.get("original_filename") or source_name
        local_name = Path(doc.get("local_path") or "").name
        sha256 = doc.get("sha256") or ""
        gemini_document_name = doc.get("gemini_document_name") or ""

        if source_name == original:
            return original

        if local_name and source_name == local_name:
            return original

        if sha256 and (source_name.startswith(sha256) or sha256 in source_name):
            return original

        if gemini_document_name and source in gemini_document_name:
            return original

    return source_name


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value


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
