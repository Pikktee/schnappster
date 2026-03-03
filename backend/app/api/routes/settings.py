from fastapi import APIRouter

from app.core.db import DbSession
from app.models.settings import AppSettings, AppSettingsRead, AppSettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=list[AppSettingsRead])
def list_settings(session: DbSession):
    return session.query(AppSettings).all()


@router.get("/{key}", response_model=AppSettingsRead)
def get_setting(key: str, session: DbSession):
    setting = session.get(AppSettings, key)
    if not setting:
        from app.services.settings import DEFAULTS

        if key in DEFAULTS:
            return AppSettingsRead(key=key, value=DEFAULTS[key])
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.put("/{key}", response_model=AppSettingsRead)
def update_setting(key: str, data: AppSettingsUpdate, session: DbSession):
    setting = session.get(AppSettings, key)
    if setting:
        setting.value = data.value
    else:
        setting = AppSettings(key=key, value=data.value)
        session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting
