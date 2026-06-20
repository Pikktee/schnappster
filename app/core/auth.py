"""Eigene JWT-Auth: Token-Erzeugung, -Pruefung und FastAPI-Dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session

from app.core.config import config
from app.core.db import get_session
from app.models.user import User

_JWT_ALGORITHM = "HS256"


@dataclass(slots=True)
class CurrentUser:
    """Authentifizierter Benutzer aus dem dekodierten Access-Token + DB."""

    id: str
    email: str
    role: str

    @property
    def user_id(self) -> str:
        """Eigentuemer-ID fuer owner_id-Filter."""
        return self.id


def create_access_token(user: User) -> str:
    """Signiert ein kurzlebiges JWT (HS256) fuer den Benutzer."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=config.access_token_expire_minutes)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=_JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, config.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return parts[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),  # noqa: B008
) -> CurrentUser:
    """Dekodiert das Bearer-JWT lokal, laedt den Benutzer und prueft die Freischaltung."""
    token = _extract_bearer_token(authorization)
    payload = _decode_token(token)
    user_id = str(payload.get("sub") or "").strip()
    user = session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Konto nicht gefunden oder nicht freigeschaltet.",
        )
    return CurrentUser(id=user.id, email=user.email, role=user.role)


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
    """Erlaubt Zugriff nur fuer Admin-Rolle."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
