"""HTTP client for the Schnappster FastAPI (Bearer auth)."""

from typing import Any

import httpx

from schnappster_mcp.core.config import Settings


def _format_fastapi_detail(detail: Any) -> str:
    """Baut eine lesbare Fehlermeldung aus FastAPI-``detail`` (str, Liste von Errors, dict)."""
    if detail is None:
        return ""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict) and "msg" in item:
                parts.append(str(item["msg"]))
            else:
                parts.append(str(item))
        return " ".join(p for p in parts if p)
    if isinstance(detail, dict):
        return str(detail)
    return str(detail)


class SchnappsterApiError(Exception):
    """Raised when the API returns a non-success status."""

    def __init__(self, status_code: int, message: str) -> None:
        """Speichert den HTTP-Status und übergibt ``message`` an ``Exception``."""
        self.status_code = status_code
        super().__init__(message)


class SchnappsterApiClient:
    """Async HTTP-Client gegen die Schnappster-REST-API mit Bearer-Token."""

    def __init__(self, settings: Settings, access_token: str) -> None:
        """Initialisiert Basis-URL und Zugriffstoken."""
        self._base = str(settings.schnappster_api_base_url).rstrip("/")
        self._token = access_token

    def _headers(self) -> dict[str, str]:
        """Standard-Header inkl. ``Authorization: Bearer`` und ``Content-Type``."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> Any:
        """Führt eine HTTP-Anfrage aus; bei Erfolg JSON (oder ``None`` bei 204/leerem Body)."""
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json_body,
            )

        if response.status_code == 204:
            return None

        if response.is_success:
            if not response.content:
                return None
            return response.json()

        body: dict[str, Any] = {}
        try:
            body = response.json()
        except Exception:
            body = {}
        detail = body.get("detail")
        msg = _format_fastapi_detail(detail) or response.text or f"HTTP {response.status_code}"
        raise SchnappsterApiError(response.status_code, msg)
