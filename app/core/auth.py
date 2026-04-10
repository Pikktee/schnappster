"""Supabase-basierte Auth-Dependencies fuer FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.core.config import config


@dataclass(slots=True)
class CurrentUser:
    """Minimales User-Objekt aus dem Supabase-Auth-User-Endpunkt."""

    id: str
    email: str | None
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]
    access_token: str

    @property
    def role(self) -> str:
        """Rolle aus app_metadata oder Fallback 'user'."""
        return str(self.app_metadata.get("role", "user"))


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


def _require_supabase_auth_config() -> None:
    if not config.supabase_url or not config.supabase_publishable_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured on the server",
        )


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Validiert Bearer-Token ueber Supabase und liefert User-Claims."""
    _require_supabase_auth_config()
    access_token = _extract_bearer_token(authorization)
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": config.supabase_publishable_key,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth upstream unavailable: {exc}",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    data = response.json()
    return CurrentUser(
        id=str(data.get("id", "")),
        email=data.get("email"),
        app_metadata=data.get("app_metadata") or {},
        user_metadata=data.get("user_metadata") or {},
        access_token=access_token,
    )


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
    """Erlaubt Zugriff nur fuer Admin-Rolle."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user

