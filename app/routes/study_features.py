from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.schemas import (
    BriefingRequest,
    FaqRequest,
    StudyFeatureResponse,
    StudyGuideRequest,
    TimelineRequest,
)
from app.security import require_internal_token
from app.services.study_features_service import (
    create_briefing,
    extract_timeline,
    generate_faq,
    generate_study_guide,
)

router = APIRouter(prefix="/features", dependencies=[Depends(require_internal_token)])


@router.post("/study-guide", response_model=StudyFeatureResponse)
def study_guide(payload: StudyGuideRequest) -> StudyFeatureResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return generate_study_guide(store, payload.topic, payload.level)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini study guide failed: {exc}") from exc


@router.post("/faq", response_model=StudyFeatureResponse)
def faq(payload: FaqRequest) -> StudyFeatureResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return generate_faq(store, payload.nQuestions)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini FAQ failed: {exc}") from exc


@router.post("/briefing", response_model=StudyFeatureResponse)
def briefing(payload: BriefingRequest) -> StudyFeatureResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return create_briefing(store, payload.audience)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini briefing failed: {exc}") from exc


@router.post("/timeline", response_model=StudyFeatureResponse)
def timeline(payload: TimelineRequest) -> StudyFeatureResponse:
    store = _get_store(payload.tenantId, payload.storeKey)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    try:
        return extract_timeline(store)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini timeline failed: {exc}") from exc


def _get_store(tenant_id: str, store_key: str) -> dict | None:
    with get_db() as conn:
        return conn.execute(
            """
            SELECT * FROM stores
            WHERE tenant_id = ? AND store_key = ?
            """,
            (tenant_id, store_key),
        ).fetchone()
