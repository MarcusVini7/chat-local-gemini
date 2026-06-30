from fastapi import APIRouter

from app.config import settings


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
