"""FastMCP app: Streamable HTTP, Supabase auth, Schnappster API tools."""

import base64
from collections.abc import Awaitable
from importlib.resources import files
from typing import Literal
from urllib.parse import urlparse

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import Icon
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse

from schnappster_mcp.api_client import SchnappsterApiClient, SchnappsterApiError
from schnappster_mcp.auth import SupabaseTokenVerifier
from schnappster_mcp.config import Settings


async def _run_api[T](coro: Awaitable[T]) -> T:
    try:
        return await coro
    except SchnappsterApiError as exc:
        raise ToolError(f"Schnappster-API ({exc.status_code}): {exc}") from exc


def _log_level(value: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    upper = value.upper()
    if upper in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        return upper  # type: ignore[return-value]
    return "INFO"


def _api_client(settings: Settings) -> SchnappsterApiClient:
    access = get_access_token()
    if access is None:
        raise ToolError(
            "Nicht authentifiziert: gültiges Bearer-Token (Supabase Access Token) erforderlich."
        )
    return SchnappsterApiClient(settings, access.token)


def _schnappster_mcp_icons() -> list[Icon]:
    """Gleiches 32×32-PNG wie Next.js `app/icon.png` (für MCP-Client-Branding, z. B. Claude)."""
    raw = files("schnappster_mcp").joinpath("icon.png").read_bytes()
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return [Icon(src=f"data:image/png;base64,{b64}", mimeType="image/png", sizes=["32x32"])]


def _transport_security(settings: Settings) -> TransportSecuritySettings | None:
    """DNS-Rebinding-Schutz wie FastMCP für Loopback, plus Host aus öffentlicher MCP-URL (Tunnel).

    Ohne Eintrag für z. B. ``*.trycloudflare.com`` lehnt Starlette POSTs nach OAuth mit
    ``Invalid Host header`` ab (Host-Header = öffentliche Domain, Server bindet auf 127.0.0.1).
    """
    if settings.mcp_host not in ("127.0.0.1", "localhost", "::1"):
        return None

    allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    allowed_origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
    ]
    public = settings.mcp_resource_server_url
    assert public is not None
    parsed = urlparse(str(public))
    hostname = parsed.hostname
    if hostname and hostname not in ("127.0.0.1", "localhost", "::1"):
        port = parsed.port
        if port is not None and port not in (80, 443):
            allowed_hosts.append(f"{hostname}:{port}")
        else:
            allowed_hosts.append(hostname)
        scheme = parsed.scheme if parsed.scheme in ("http", "https") else "https"
        allowed_origins.append(f"{scheme}://{hostname}:*")

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def build_mcp(settings: Settings) -> FastMCP:
    resource = settings.mcp_resource_server_url
    assert resource is not None

    mcp = FastMCP(
        name="Schnappster",
        instructions=(
            "Zugriff auf Schnappster: Schnäppchen (Ads mit Score), persönliche "
            "Benutzereinstellungen und Suchaufträge (Ad Searches). "
            "Authentifizierung: Supabase Access Token als Bearer (wie im Web-Frontend)."
        ),
        icons=_schnappster_mcp_icons(),
        json_response=True,
        token_verifier=SupabaseTokenVerifier(settings),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(settings.supabase_auth_issuer_url),
            resource_server_url=resource,
            required_scopes=None,
        ),
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path=settings.streamable_http_path,
        log_level=_log_level(settings.log_level),
        transport_security=_transport_security(settings),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(_request: Request) -> JSONResponse:  # noqa: ARG001
        return JSONResponse({"status": "ok"})

    @mcp.tool()
    async def list_recent_bargains(
        limit: int = 24,
        offset: int = 0,
        min_score: int | None = None,
        adsearch_id: int | None = None,
    ) -> dict:
        """Listet analysierte Anzeigen, sortiert nach Schnäppchen-Score (höchste zuerst)."""
        lim = min(max(limit, 1), 100)
        params: dict[str, str | int] = {
            "sort": "score-desc",
            "is_analyzed": "true",
            "limit": lim,
            "offset": max(offset, 0),
        }
        if min_score is not None and min_score > 0:
            params["min_score"] = min_score
        if adsearch_id is not None:
            params["adsearch_id"] = adsearch_id
        client = _api_client(settings)
        return await _run_api(client.request("GET", "/api/ads/", params=params))

    @mcp.tool()
    async def get_my_settings() -> dict:
        """Liest persönliche Benutzereinstellungen (Benachrichtigungen, Telegram, Mindest-Score)."""
        client = _api_client(settings)
        return await _run_api(client.request("GET", "/api/users/me/settings"))

    @mcp.tool()
    async def update_my_settings(
        display_name: str | None = None,
        telegram_chat_id: str | None = None,
        notify_telegram: bool | None = None,
        notify_email: bool | None = None,
        notify_min_score: int | None = None,
    ) -> dict:
        """Aktualisiert persönliche Einstellungen (nur angegebene Felder)."""
        body: dict[str, str | bool | int] = {}
        if display_name is not None:
            body["display_name"] = display_name
        if telegram_chat_id is not None:
            body["telegram_chat_id"] = telegram_chat_id
        if notify_telegram is not None:
            body["notify_telegram"] = notify_telegram
        if notify_email is not None:
            body["notify_email"] = notify_email
        if notify_min_score is not None:
            body["notify_min_score"] = notify_min_score
        if not body:
            raise ToolError("Mindestens ein Feld zum Aktualisieren angeben.")
        client = _api_client(settings)
        return await _run_api(client.request("PATCH", "/api/users/me/settings", json_body=body))

    @mcp.tool()
    async def list_ad_searches() -> list:
        """Listet alle Suchaufträge des Nutzers."""
        client = _api_client(settings)
        return await _run_api(client.request("GET", "/api/adsearches/"))

    @mcp.tool()
    async def get_ad_search(adsearch_id: int) -> dict:
        """Holt einen Suchauftrag anhand der ID."""
        client = _api_client(settings)
        return await _run_api(client.request("GET", f"/api/adsearches/{adsearch_id}"))

    @mcp.tool()
    async def create_ad_search(
        url: str,
        name: str = "",
        prompt_addition: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        blacklist_keywords: str | None = None,
        is_exclude_images: bool = False,
        is_active: bool = True,
        scrape_interval_minutes: int = 30,
    ) -> dict:
        """Legt einen neuen Suchauftrag an (Kleinanzeigen-Suchergebnis-URL erforderlich)."""
        raw: dict[str, str | float | bool | int | None] = {
            "url": url,
            "name": name,
            "prompt_addition": prompt_addition,
            "min_price": min_price,
            "max_price": max_price,
            "blacklist_keywords": blacklist_keywords,
            "is_exclude_images": is_exclude_images,
            "is_active": is_active,
            "scrape_interval_minutes": scrape_interval_minutes,
        }
        body = {k: v for k, v in raw.items() if v is not None}
        client = _api_client(settings)
        return await _run_api(client.request("POST", "/api/adsearches/", json_body=body))

    @mcp.tool()
    async def update_ad_search(
        adsearch_id: int,
        name: str | None = None,
        url: str | None = None,
        prompt_addition: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        blacklist_keywords: str | None = None,
        is_exclude_images: bool | None = None,
        is_active: bool | None = None,
        scrape_interval_minutes: int | None = None,
    ) -> dict:
        """Aktualisiert einen Suchauftrag (nur gesetzte Felder)."""
        body: dict[str, str | float | bool | int] = {}
        if name is not None:
            body["name"] = name
        if url is not None:
            body["url"] = url
        if prompt_addition is not None:
            body["prompt_addition"] = prompt_addition
        if min_price is not None:
            body["min_price"] = min_price
        if max_price is not None:
            body["max_price"] = max_price
        if blacklist_keywords is not None:
            body["blacklist_keywords"] = blacklist_keywords
        if is_exclude_images is not None:
            body["is_exclude_images"] = is_exclude_images
        if is_active is not None:
            body["is_active"] = is_active
        if scrape_interval_minutes is not None:
            body["scrape_interval_minutes"] = scrape_interval_minutes
        if not body:
            raise ToolError("Mindestens ein Feld zum Aktualisieren angeben.")
        client = _api_client(settings)
        return await _run_api(
            client.request("PATCH", f"/api/adsearches/{adsearch_id}", json_body=body)
        )

    @mcp.tool()
    async def delete_ad_search(adsearch_id: int) -> dict:
        """Löscht einen Suchauftrag inkl. zugehöriger Daten."""
        client = _api_client(settings)
        await _run_api(client.request("DELETE", f"/api/adsearches/{adsearch_id}"))
        return {"deleted": True, "adsearch_id": adsearch_id}

    return mcp
