import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    expected_token = settings.internal_api_token
    if not expected_token:
        return
    if not x_internal_token or not secrets.compare_digest(x_internal_token, expected_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing internal token",
        )
