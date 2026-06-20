"""Token-Pruefung gegen die Schnappster-API (eigene JWT-Auth, kein Supabase mehr)."""

import contextlib

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier

from schnappster_mcp.core.config import Settings


class ApiTokenVerifier(TokenVerifier):
    """Validiert Bearer-Tokens per ``GET /users/me/`` gegen die Schnappster-API."""

    def __init__(self, settings: Settings) -> None:
        """Haelt die geladenen Einstellungen (API-Basis-URL)."""
        self._settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        """Prueft ``token`` per ``GET /users/me/``.

        Rueckgabe: ``AccessToken`` bei HTTP 200, sonst ``None``.
        """
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._settings.users_me_url, headers=headers)
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None

        client_id = "schnappster-user"
        with contextlib.suppress(ValueError):
            client_id = str(response.json().get("id") or client_id)

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=[],
            expires_at=None,
            resource=None,
        )
