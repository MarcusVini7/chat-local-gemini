from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.security import require_internal_token
from app.services.settings_service import (
    get_active_gemini_model,
    get_active_gemini_model_source,
    list_allowed_gemini_models,
    set_active_gemini_model,
)


router = APIRouter(dependencies=[Depends(require_internal_token)])


class ModelUpdateRequest(BaseModel):
    model: str = Field(min_length=1)


@router.get("/settings/model")
def get_model_setting() -> dict:
    return {
        "activeModel": get_active_gemini_model(),
        "envDefaultModel": settings.gemini_model,
        "allowedModels": list_allowed_gemini_models(),
        "source": get_active_gemini_model_source(),
    }


@router.patch("/settings/model")
def update_model_setting(payload: ModelUpdateRequest) -> dict:
    try:
        set_active_gemini_model(payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Model not allowed") from exc
    return {
        "activeModel": payload.model,
        "allowedModels": list_allowed_gemini_models(),
        "updated": True,
    }
