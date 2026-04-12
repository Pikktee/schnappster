"""Supabase access-token verification (same idea as Schnappster FastAPI `get_current_user`)."""

from mcp.server.auth.provider import AccessToken, TokenVerifier

from schnappster_mcp.config import Settings


class SupabaseTokenVerifier(TokenVerifier):
    """Validates Bearer tokens via `GET /auth/v1/user`."""

    def __init__(self, settings: Settings) -> None:
        """Hält die geladenen Einstellungen (Supabase-URL, Publishable Key)."""
        self._settings = settings

    async def verify_token(self, token: str) -> AccessToken | None:
        """Prüft ``token`` per Supabase ``GET /auth/v1/user``.

        Rückgabe: ``AccessToken`` bei HTTP 200, sonst ``None``.
        """
        import httpx

        headers = {
            "apikey": self._settings.supabase_publishable_key,
            "Authorization": f"Bearer {token}",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self._settings.supabase_user_url, headers=headers)
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None

        return AccessToken(
            token=token,
            client_id="supabase",
            scopes=[],
            expires_at=None,
            resource=None,
        )
