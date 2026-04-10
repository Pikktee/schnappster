"""API-Routen für Einstellungen."""

from fastapi import APIRouter, Depends, HTTPException

from app.core import config as app_config
from app.core.auth import CurrentUser, require_admin
from app.core.db import UserDbSession
from app.models.settings_app import AppSettingsRead, AppSettingsUpdate
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[dict])
def list_settings(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt alle unterstützten Einstellungen mit aktuellem Wert und Metadaten zurück."""
    service = SettingsService(session)
    return service.get_all()


@router.get("/telegram-configured")
def get_telegram_configured(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt an, ob Telegram global konfiguriert ist (Bot-Token vorhanden)."""
    configured = bool(app_config.telegram_bot_token.strip())

    return {"configured": configured}


@router.get("/{key}", response_model=AppSettingsRead)
def read_setting(
    key: str,
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt den Wert für einen Einstellungsschlüssel zurück; 404 wenn Schlüssel nicht
    unterstützt.
    """
    service = SettingsService(session)
    try:
        value = service.get(key)

        return AppSettingsRead(key=key, value=value)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{key}", response_model=AppSettingsRead)
def update_setting(
    key: str,
    data: AppSettingsUpdate,
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Aktualisiert eine Einstellung; validiert gegen Regeln (z. B. erlaubte Werte); 422 bei
    ungültigem Wert.
    """
    service = SettingsService(session)
    try:
        service.set(key, data.value)
        current_value = service.get(key)

        return AppSettingsRead(key=key, value=current_value)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
