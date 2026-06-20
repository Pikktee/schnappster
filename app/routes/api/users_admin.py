"""Admin-Benutzerverwaltung: Auflisten, Anlegen, Freischalten/Sperren, Loeschen, Passwort-Reset."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select

from app.core.auth import CurrentUser, require_admin
from app.core.db import SessionDep
from app.core.security import hash_password, validate_password_strength
from app.models.user import (
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserUpdate,
    User,
    UserRead,
)
from app.services.users import count_active_admins, delete_user_and_data

router = APIRouter(prefix="/admin/users", tags=["Admin: Users"])


def _get_user_or_404(session: SessionDep, user_id: str) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden."
        )
    return user


def _validate_password_or_422(password: str) -> None:
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/", response_model=list[UserRead])
def list_users(session: SessionDep, _: CurrentUser = Depends(require_admin)):  # noqa: B008
    """Gibt alle Benutzerkonten zurueck (neueste zuerst)."""
    users = session.exec(select(User).order_by(User.created_at.desc())).all()  # type: ignore[attr-defined]
    return [UserRead.model_validate(user) for user in users]


@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    payload: AdminUserCreate,
    session: SessionDep,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Legt ein Konto direkt an (standardmaessig bereits freigeschaltet)."""
    _validate_password_or_422(payload.password)
    if payload.role not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rolle muss 'user' oder 'admin' sein.",
        )
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mit dieser E-Mail existiert bereits ein Konto.",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    session: SessionDep,
    admin: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Schaltet ein Konto frei/sperrt es oder aendert die Rolle."""
    user = _get_user_or_404(session, user_id)

    would_drop_admin = user.role == "admin" and user.is_active and (
        payload.role == "user" or payload.is_active is False
    )
    if would_drop_admin and count_active_admins(session) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Der letzte aktive Admin kann nicht gesperrt oder herabgestuft werden.",
        )
    if user.id == admin.user_id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Du kannst dein eigenes Konto nicht sperren.",
        )

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role is not None:
        user.role = payload.role
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserRead.model_validate(user)


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: str,
    payload: AdminPasswordReset,
    session: SessionDep,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Setzt ein neues Passwort fuer einen Benutzer (Admin-Reset)."""
    user = _get_user_or_404(session, user_id)
    _validate_password_or_422(payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    session.add(user)
    session.commit()


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    session: SessionDep,
    admin: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Loescht ein Konto inklusive aller App-Daten."""
    user = _get_user_or_404(session, user_id)
    if user.id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eigenes Konto bitte unter 'Profil' loeschen.",
        )
    if user.role == "admin" and user.is_active and count_active_admins(session) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Der letzte aktive Admin kann nicht geloescht werden.",
        )
    delete_user_and_data(session, user.id)
