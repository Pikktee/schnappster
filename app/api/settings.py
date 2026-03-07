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
    """
    Gibt alle unterstützten Einstellungen mit ihren aktuellen Werten
    und Metadaten zurück.
    """
    service = SettingsService(session)
    return service.get_all()


@router.get("/telegram-configured")
def get_telegram_configured(session: DbSession):
    """
    Gibt zurück, ob Telegram in der .env konfiguriert ist.
    (Bot Token und Chat ID vorhanden).
    """
    configured = bool(app_config.telegram_bot_token.strip() and app_config.telegram_chat_id.strip())

    return {"configured": configured}


@router.get("/{key}", response_model=AppSettingsRead)
def read_setting(key: str, session: DbSession):
    """
    Holt den Wert für einen bestimmten Schlüssel.
    Falls der Schlüssel nicht unterstützt wird, wird ein 404 geworfen.
    """
    service = SettingsService(session)
    try:
        value = service.get(key)

        return AppSettingsRead(key=key, value=value)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{key}", response_model=AppSettingsRead)
def update_setting(key: str, data: AppSettingsUpdate, session: DbSession):
    """
    Aktualisiert den Wert einer Einstellung.
    Validiert den Wert gegen die Regeln im Service (z.B. 'allowed').
    """
    service = SettingsService(session)
    try:
        service.set(key, data.value)
        current_value = service.get(key)

        return AppSettingsRead(key=key, value=current_value)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
