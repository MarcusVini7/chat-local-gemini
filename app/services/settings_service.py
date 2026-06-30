from app.config import settings
from app.database import get_db


ACTIVE_GEMINI_MODEL_KEY = "active_gemini_model"


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> dict:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        row = conn.execute(
            "SELECT key, value, updated_at FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
    return row


def list_allowed_gemini_models() -> list[str]:
    return list(settings.gemini_allowed_models)


def get_active_gemini_model() -> str:
    saved_model = get_setting(ACTIVE_GEMINI_MODEL_KEY)
    if saved_model in settings.gemini_allowed_models:
        return saved_model
    return settings.gemini_model


def get_active_gemini_model_source() -> str:
    saved_model = get_setting(ACTIVE_GEMINI_MODEL_KEY)
    return "sqlite" if saved_model in settings.gemini_allowed_models else "env"


def set_active_gemini_model(model: str) -> dict:
    if model not in settings.gemini_allowed_models:
        raise ValueError("Model not allowed")
    return set_setting(ACTIVE_GEMINI_MODEL_KEY, model)
