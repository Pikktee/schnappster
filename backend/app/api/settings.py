from fastapi import APIRouter, HTTPException

from app.core.db import DbSession
from app.models.settings import AppSettingsRead
from app.services.settings import (
    SETTINGS_SCHEMA,
    get_all_settings,
    get_setting,
    set_setting,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_model=list[dict])
def list_settings(session: DbSession):
    return get_all_settings(session)


@router.get("/{key}", response_model=AppSettingsRead)
def read_setting(key: str, session: DbSession):
    if key not in SETTINGS_SCHEMA:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")
    value = get_setting(key, session)
    return AppSettingsRead(key=key, value=value)


@router.put("/{key}", response_model=AppSettingsRead)
def update_setting(key: str, data: dict, session: DbSession):
    try:
        set_setting(key, data.get("value", ""), session)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    value = get_setting(key, session)
    return AppSettingsRead(key=key, value=value)
