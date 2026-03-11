"""Settings API routes."""

from fastapi import APIRouter, HTTPException

from app.core import config as app_config
from app.core.db import DbSession
from app.models.settings import AppSettingsRead, AppSettingsUpdate
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


# --------------
# --- Routes ---
# --------------
@router.get("/", response_model=list[dict])
def list_settings(session: DbSession):
    """Return all supported settings with current values and metadata."""
    service = SettingsService(session)
    return service.get_all()


@router.get("/telegram-configured")
def get_telegram_configured(session: DbSession):
    """Return whether Telegram is configured in .env (bot token and chat id present)."""
    configured = bool(app_config.telegram_bot_token.strip() and app_config.telegram_chat_id.strip())

    return {"configured": configured}


@router.get("/{key}", response_model=AppSettingsRead)
def read_setting(key: str, session: DbSession):
    """Return the value for a setting key; raise 404 if key is not supported."""
    service = SettingsService(session)
    try:
        value = service.get(key)

        return AppSettingsRead(key=key, value=value)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{key}", response_model=AppSettingsRead)
def update_setting(key: str, data: AppSettingsUpdate, session: DbSession):
    """Update setting; validate against rules (e.g. allowed); raise 422 on invalid value."""
    service = SettingsService(session)
    try:
        service.set(key, data.value)
        current_value = service.get(key)

        return AppSettingsRead(key=key, value=current_value)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
