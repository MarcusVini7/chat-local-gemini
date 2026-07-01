"""
Serviço de recursos extras de estudo, no estilo NotebookLM.

Reaproveita o Gemini File Search já configurado (answer_store_prompt) para
gerar guia de estudos, FAQ, briefing executivo e timeline a partir das fontes
de uma store — sem depender de LangChain/ChromaDB/LlamaCpp.
"""
from app.schemas import StudyFeatureResponse
from app.services.answer_service import answer_store_prompt
from app.services.prompt_service import (
    briefing_prompt,
    faq_prompt,
    study_guide_prompt,
    timeline_prompt,
)


def generate_study_guide(store: dict, topic: str, level: str) -> StudyFeatureResponse:
    response = answer_store_prompt(store, study_guide_prompt(topic, level))
    return _to_feature_response(response)


def generate_faq(store: dict, n_questions: int) -> StudyFeatureResponse:
    response = answer_store_prompt(store, faq_prompt(n_questions))
    return _to_feature_response(response)


def create_briefing(store: dict, audience: str) -> StudyFeatureResponse:
    response = answer_store_prompt(store, briefing_prompt(audience))
    return _to_feature_response(response)


def extract_timeline(store: dict) -> StudyFeatureResponse:
    response = answer_store_prompt(store, timeline_prompt())
    return _to_feature_response(response)


def _to_feature_response(response) -> StudyFeatureResponse:
    return StudyFeatureResponse(
        content=response.answer,
        citations=response.citations,
        confidence=response.confidence,
        reason=response.reason,
    )
