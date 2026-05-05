"""API-Routen fuer Profil, User-Settings und Konto-Management."""

from __future__ import annotations

import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel, select

from app.core.auth import CurrentUser, get_current_user, identity_display_name
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
    old_password: str
    new_password: str


class DeleteAccountRequest(SQLModel):
    confirm_email: str


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


def _verify_email_password(email: str, password: str) -> None:
    """Prueft das Passwort per Supabase Password-Grant (ohne Session zu ersetzen)."""
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": config.supabase_publishable_key,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=config.supabase_auth_timeout) as client:
        response = client.post(
            url,
            headers=headers,
            json={"email": email.strip(), "password": password},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Altes Passwort ist falsch.",
        )


def _delete_auth_user(user_id: str) -> None:
    secret_key = _ensure_supabase_secret_key()
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
    }
    with httpx.Client(timeout=config.supabase_auth_timeout) as client:
        response = client.delete(url, headers=headers)
    if response.status_code not in {200, 204, 404}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete auth user: {response.text}",
        )


def _validate_password_strength(password: str) -> None:
    """Prueft Mindestlaenge, Gross-/Kleinbuchstaben und Sonderzeichen."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("mindestens 8 Zeichen")
    if not re.search(r"[A-Z]", password):
        errors.append("einen Grossbuchstaben")
    if not re.search(r"[a-z]", password):
        errors.append("einen Kleinbuchstaben")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("ein Sonderzeichen")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Passwort benoetigt: {', '.join(errors)}.",
        )


@router.get("/", response_model=UserProfileRead)
def get_me(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    settings = service.hydrate_display_name_from_identity(
        current_user.user_id,
        identity_display_name(current_user),
    )
    avatar_url = current_user.user_metadata.get("avatar_url")
    id_name = identity_display_name(current_user)
    profile_name = (
        settings.display_name
        if settings.display_name_user_set
        else (settings.display_name or id_name)
    )
    return UserProfileRead(
        id=current_user.user_id,
        email=current_user.email,
        display_name=profile_name,
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
    settings = service.hydrate_display_name_from_identity(
        current_user.user_id,
        identity_display_name(current_user),
    )
    settings.display_name = data.display_name
    settings.display_name_user_set = True
    session.add(settings)
    session.commit()
    session.refresh(settings)
    avatar_url = current_user.user_metadata.get("avatar_url")
    id_name = identity_display_name(current_user)
    profile_name = (
        settings.display_name
        if settings.display_name_user_set
        else (settings.display_name or id_name)
    )
    return UserProfileRead(
        id=current_user.user_id,
        email=current_user.email,
        display_name=profile_name,
        avatar_url=str(avatar_url) if avatar_url else None,
        role=current_user.role,
    )


@router.get("/settings", response_model=UserSettingsRead)
def get_my_settings(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    return service.hydrate_display_name_from_identity(
        current_user.user_id,
        identity_display_name(current_user),
    )


@router.patch("/settings", response_model=UserSettingsRead)
def patch_my_settings(
    data: UserSettingsUpdate,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    try:
        return service.update_user_settings(current_user.user_id, data)
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
            detail="Passwort aendern ist nur fuer E-Mail-/Passwort-Konten moeglich.",
        )
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keine E-Mail fuer dieses Konto hinterlegt.",
        )
    new_pw = payload.new_password.strip()
    _validate_password_strength(new_pw)
    _verify_email_password(current_user.email, payload.old_password)
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/user"
    with httpx.Client(timeout=config.supabase_auth_timeout) as client:
        response = client.put(
            url,
            headers=_supabase_headers(current_user.access_token),
            json={"password": new_pw},
        )
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwort konnte nicht aktualisiert werden.",
        )


@router.delete("/", status_code=204)
def delete_me(
    session: UserDbSession,
    payload: DeleteAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Keine E-Mail fuer dieses Konto hinterlegt "
                "(Bestaetigung per E-Mail nicht moeglich)."
            ),
        )
    confirmed = payload.confirm_email.strip().casefold()
    expected = current_user.email.strip().casefold()
    if confirmed != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-Mail stimmt nicht mit dem Konto ueberein.",
        )
    # Schutz fuer den primaeren Admin.
    if current_user.role == "admin" and config.primary_admin_user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Primary admin account cannot be deleted",
        )

    user_settings = session.get(UserSettings, current_user.user_id)
    if not user_settings:
        user_settings = UserSettings(
            user_id=current_user.user_id,
            display_name=identity_display_name(current_user),
        )
        session.add(user_settings)
        session.commit()
        session.refresh(user_settings)

    ad_searches = session.exec(
        select(AdSearch).where(AdSearch.owner_id == current_user.user_id)
    ).all()
    for ad_search in ad_searches:
        session.delete(ad_search)
    if user_settings:
        session.delete(user_settings)
    session.commit()

    try:
        _delete_auth_user(current_user.user_id)
    except HTTPException:
        # Falls Auth-Delete fehlschlaegt, markieren und Retry erlauben.
        pending = session.get(UserSettings, current_user.user_id)
        if pending is None:
            pending = UserSettings(
                user_id=current_user.user_id,
                display_name=identity_display_name(current_user),
                deletion_pending=True,
            )
        else:
            pending.deletion_pending = True
        session.add(pending)
        session.commit()
        raise
