"""API-Routen fuer Profil, User-Settings und Konto-Management."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel, select

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config
from app.core.db import UserDbSession
from app.models.adsearch import AdSearch
from app.models.settings_user import (
    UserProfileRead,
    UserProfileUpdate,
    UserSettings,
    UserSettingsRead,
    UserSettingsUpdate,
)
from app.services.settings import SettingsService

router = APIRouter(prefix="/users/me", tags=["Users"])


class ChangePasswordRequest(SQLModel):
    new_password: str


def _ensure_supabase_secret_key() -> str:
    key = config.supabase_secret_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase admin API is not configured",
        )
    return key


def _supabase_headers(token: str) -> dict[str, str]:
    return {
        "apikey": config.supabase_publishable_key,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_display_name(current_user: CurrentUser) -> str:
    return str(
        current_user.user_metadata.get("full_name")
        or current_user.user_metadata.get("name")
        or ""
    )


def _delete_auth_user(user_id: str) -> None:
    secret_key = _ensure_supabase_secret_key()
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.delete(url, headers=headers)
    if response.status_code not in {200, 204, 404}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete auth user: {response.text}",
        )


@router.get("/", response_model=UserProfileRead)
def get_me(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    settings = service.get_user_settings(
        current_user.id,
        default_display_name=_get_display_name(current_user),
    )
    avatar_url = current_user.user_metadata.get("avatar_url")
    return UserProfileRead(
        id=current_user.id,
        email=current_user.email,
        display_name=settings.display_name or _get_display_name(current_user),
        avatar_url=str(avatar_url) if avatar_url else None,
        role=current_user.role,
    )


@router.patch("/", response_model=UserProfileRead)
def patch_me(
    data: UserProfileUpdate,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    settings = service.get_user_settings(
        current_user.id,
        default_display_name=_get_display_name(current_user),
    )
    settings.display_name = data.display_name.strip()
    session.add(settings)
    session.commit()
    session.refresh(settings)
    avatar_url = current_user.user_metadata.get("avatar_url")
    return UserProfileRead(
        id=current_user.id,
        email=current_user.email,
        display_name=settings.display_name,
        avatar_url=str(avatar_url) if avatar_url else None,
        role=current_user.role,
    )


@router.get("/settings", response_model=UserSettingsRead)
def get_my_settings(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    return service.get_user_settings(
        current_user.id,
        default_display_name=_get_display_name(current_user),
    )


@router.patch("/settings", response_model=UserSettingsRead)
def patch_my_settings(
    data: UserSettingsUpdate,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    try:
        return service.update_user_settings(current_user.id, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    providers = current_user.app_metadata.get("providers") or []
    if "email" not in providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change is only available for email/password accounts",
        )
    if len(payload.new_password.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must have at least 8 characters",
        )
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/user"
    with httpx.Client(timeout=10.0) as client:
        response = client.put(
            url,
            headers=_supabase_headers(current_user.access_token),
            json={"password": payload.new_password},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password update failed",
        )


@router.delete("/", status_code=204)
def delete_me(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    # Schutz fuer den primaeren Admin.
    if current_user.role == "admin" and config.primary_admin_user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Primary admin account cannot be deleted",
        )

    user_settings = session.get(UserSettings, current_user.id)
    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.id,
            display_name=_get_display_name(current_user),
        )
        session.add(user_settings)
        session.commit()
        session.refresh(user_settings)

    ad_searches = session.exec(select(AdSearch).where(AdSearch.owner_id == current_user.id)).all()
    for ad_search in ad_searches:
        session.delete(ad_search)
    if user_settings:
        session.delete(user_settings)
    session.commit()

    try:
        _delete_auth_user(current_user.id)
    except HTTPException:
        # Falls Auth-Delete fehlschlaegt, markieren und Retry erlauben.
        pending = session.get(UserSettings, current_user.id)
        if pending is None:
            pending = UserSettings(
                user_id=current_user.id,
                display_name=_get_display_name(current_user),
                deletion_pending=True,
            )
        else:
            pending.deletion_pending = True
        session.add(pending)
        session.commit()
        raise
