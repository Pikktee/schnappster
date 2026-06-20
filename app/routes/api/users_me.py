"""API-Routen fuer Profil, User-Settings und Konto-Management (eigene Auth)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel

from app.core.auth import CurrentUser, get_current_user
from app.core.db import SessionDep
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.settings_user import (
    UserProfileRead,
    UserProfileUpdate,
    UserSettingsRead,
    UserSettingsUpdate,
)
from app.models.user import User
from app.services.settings import SettingsService
from app.services.users import count_active_admins, delete_user_and_data

router = APIRouter(prefix="/users/me", tags=["Users"])


class ChangePasswordRequest(SQLModel):
    old_password: str
    new_password: str


class DeleteAccountRequest(SQLModel):
    confirm_email: str


def _profile(session: SessionDep, current_user: CurrentUser) -> UserProfileRead:
    service = SettingsService(session)
    settings = service.get_user_settings(current_user.user_id)
    user = session.get(User, current_user.user_id)
    display_name = settings.display_name or (user.display_name if user else "")
    return UserProfileRead(
        id=current_user.user_id,
        email=current_user.email,
        display_name=display_name,
        avatar_url=None,
        role=current_user.role,
    )


@router.get("/", response_model=UserProfileRead)
def get_me(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    return _profile(session, current_user)


@router.patch("/", response_model=UserProfileRead)
def patch_me(
    data: UserProfileUpdate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    settings = service.get_user_settings(current_user.user_id)
    settings.display_name = data.display_name
    settings.display_name_user_set = True
    session.add(settings)
    session.commit()
    return _profile(session, current_user)


@router.get("/settings", response_model=UserSettingsRead)
def get_my_settings(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    service = SettingsService(session)
    return service.get_user_settings(current_user.user_id)


@router.patch("/settings", response_model=UserSettingsRead)
def patch_my_settings(
    data: UserSettingsUpdate,
    session: SessionDep,
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
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    user = session.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Konto nicht gefunden.")
    new_pw = payload.new_password.strip()
    try:
        validate_password_strength(new_pw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Altes Passwort ist falsch."
        )
    user.password_hash = hash_password(new_pw)
    session.add(user)
    session.commit()


@router.delete("/", status_code=204)
def delete_me(
    session: SessionDep,
    payload: DeleteAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    confirmed = payload.confirm_email.strip().casefold()
    expected = (current_user.email or "").strip().casefold()
    if not expected or confirmed != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-Mail stimmt nicht mit dem Konto ueberein.",
        )
    if current_user.role == "admin" and count_active_admins(session) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Der letzte aktive Admin kann nicht geloescht werden.",
        )
    delete_user_and_data(session, current_user.user_id)
