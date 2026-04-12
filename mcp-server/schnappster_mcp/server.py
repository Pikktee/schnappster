"""FastMCP app: Streamable HTTP, Supabase auth, Schnappster API tools."""

import base64
from collections.abc import Awaitable
from functools import lru_cache
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
from starlette.responses import JSONResponse, Response

from schnappster_mcp.core.api_client import SchnappsterApiClient, SchnappsterApiError
from schnappster_mcp.core.auth import SupabaseTokenVerifier
from schnappster_mcp.core.config import Settings
from schnappster_mcp.mcp_ui.mcp_apps import (
    ad_searches_tool_meta,
    recent_bargains_tool_meta,
    register_mcp_apps,
)

_FAVICON_CACHE_CONTROL_MAX_AGE_S = 86400


@lru_cache(maxsize=1)
def _schnappster_mcp_icon_png_bytes() -> bytes:
    """PNG-Rohbytes für MCP-Icons und Favicon-Routen (wie ``web/app/icon.png``)."""
    return files("schnappster_mcp").joinpath("assets", "icon.png").read_bytes()


async def _run_api[T](coro: Awaitable[T]) -> T:
    """Wartet auf ``coro`` und wandelt ``SchnappsterApiError`` in ``ToolError`` um."""
    try:
        return await coro
    except SchnappsterApiError as exc:
        raise ToolError(f"Schnappster-API ({exc.status_code}): {exc}") from exc


def _log_level(value: str) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Mappt freie Log-Level-Strings auf erlaubte Uvicorn/FastMCP-Levelnamen (Fallback: INFO)."""
    upper = value.upper()
    if upper in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        return upper  # type: ignore[return-value]
    return "INFO"


def _api_client(settings: Settings) -> SchnappsterApiClient:
    """Erzeugt einen API-Client mit dem aktuellen MCP-Bearer-Token oder wirft ``ToolError``."""
    access = get_access_token()
    if access is None:
        raise ToolError(
            "Nicht authentifiziert: gültiges Bearer-Token (Supabase Access Token) erforderlich."
        )
    return SchnappsterApiClient(settings, access.token)


def _schnappster_mcp_icons() -> list[Icon]:
    """Gleiches 32×32-PNG wie Next.js `app/icon.png` (für MCP-Client-Branding, z. B. Claude)."""
    raw = _schnappster_mcp_icon_png_bytes()
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
    """Baut die FastMCP-Instanz inkl. Auth, Tools, Health- und Branding-Routen."""
    resource = settings.mcp_resource_server_url
    assert resource is not None

    # Pro Tool in tools/list — viele Clients (z. B. Claude „Tool Use“) nutzen diese Felder,
    # nicht nur serverInfo.icons aus initialize.
    tool_icons = _schnappster_mcp_icons()

    mcp = FastMCP(
        name="Schnappster",
        instructions=(
            "Zugriff auf Schnappster: Schnäppchen (Ads mit Score), persönliche "
            "Benutzereinstellungen und Suchaufträge (Ad Searches). "
            "Authentifizierung: Supabase Access Token als Bearer (wie im Web-Frontend). "
            "In Antworten an Endnutzer keine internen numerischen IDs (z. B. von Anzeigen "
            "oder Suchaufträgen) nennen; stattdessen Titel, Name des Suchauftrags oder "
            "Kurzbeschreibung verwenden. IDs nur still für Folge-Tool-Aufrufe nutzen. "
            "MCP-Apps (eingebettete Oberfläche bei list_recent_bargains, list_ad_searches, "
            "show_bargain_detail): Schreibe **vor** dem jeweiligen Tool-Aufruf 1–3 Sätze "
            "Nutzer-Text (Kontext, Einordnung, Trefferzahl bzw. Anzahl Suchaufträge). "
            "Rufe das Tool **danach** auf. Die App zeigt nur die kompakte Tabelle bzw. Karte — "
            "keine Trefferzeile und keine Zähler in der App; Zusammenfassungen gehören in den "
            "Chat-Text. Für Details zu einer Anzeige: show_bargain_detail (falls der Client "
            "ext-apps unterstützt)."
        ),
        icons=tool_icons,
        json_response=True,
        # Keine serverseitige MCP-Session: vermeidet „session … no longer exists“ bei
        # Deploys, mehreren Instanzen, Tunnel-Reconnects und längeren Client-Pausen.
        stateless_http=True,
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
        """Einfacher Liveness-Check für Loadbalancer und Tunnel-Health."""
        return JSONResponse({"status": "ok"})

    def _branding_png_response() -> Response:
        """PNG-Antwort mit Cache-Header für Favicon- und Icon-Routen."""
        return Response(
            content=_schnappster_mcp_icon_png_bytes(),
            media_type="image/png",
            headers={
                "Cache-Control": f"public, max-age={_FAVICON_CACHE_CONTROL_MAX_AGE_S}",
            },
        )

    @mcp.custom_route("/favicon.ico", methods=["GET"])
    async def favicon_ico(_request: Request) -> Response:  # noqa: ARG001
        """Favicon: Clients holen Icons oft von der Connector-Origin, nicht nur ``initialize``."""
        return _branding_png_response()

    @mcp.custom_route("/apple-touch-icon.png", methods=["GET"])
    async def apple_touch_icon(_request: Request) -> Response:  # noqa: ARG001
        """Apple-Touch-Icon (gleiches PNG wie Favicon)."""
        return _branding_png_response()

    @mcp.custom_route("/icon.png", methods=["GET"])
    async def icon_png(_request: Request) -> Response:  # noqa: ARG001
        """Explizite ``/icon.png``-Route für Clients, die diesen Pfad erwarten."""
        return _branding_png_response()

    @mcp.tool(icons=tool_icons, meta=recent_bargains_tool_meta())
    async def list_recent_bargains(
        limit: int = 24,
        offset: int = 0,
        min_score: int | None = None,
        adsearch_id: int | None = None,
    ) -> dict:
        """Listet analysierte Anzeigen, sortiert nach Schnäppchen-Score (höchste zuerst).

        Vor dem Aufruf kurz an den Nutzer schreiben (inkl. Trefferzahl); die MCP-App ist nur
        die sortierbare Tabelle ohne eigene Zählerzeile.
        """
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
        return await _run_api(client.request("GET", "/ads/", params=params))

    @mcp.tool(icons=tool_icons)
    async def get_my_settings() -> dict:
        """Liest persönliche Benutzereinstellungen (Benachrichtigungen, Telegram, Mindest-Score)."""
        client = _api_client(settings)
        return await _run_api(client.request("GET", "/users/me/settings"))

    @mcp.tool(icons=tool_icons)
    async def update_my_settings(
        display_name: str | None = None,
        telegram_chat_id: str | None = None,
        notify_telegram: bool | None = None,
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
        if notify_min_score is not None:
            body["notify_min_score"] = notify_min_score
        if not body:
            raise ToolError("Mindestens ein Feld zum Aktualisieren angeben.")
        client = _api_client(settings)
        return await _run_api(client.request("PATCH", "/users/me/settings", json_body=body))

    @mcp.tool(icons=tool_icons, meta=ad_searches_tool_meta())
    async def list_ad_searches() -> dict:
        """Listet alle Suchaufträge; Antwort als Objekt mit ``items`` (kein Top-Level-Array).

        Vor dem Aufruf kurz an den Nutzer schreiben (inkl. Anzahl Suchaufträge); die MCP-App
        zeigt keine separate Zählerzeile.
        """
        client = _api_client(settings)
        rows = await _run_api(client.request("GET", "/adsearches/"))
        if not isinstance(rows, list):
            rows = []
        return {"items": rows, "total": len(rows)}

    @mcp.tool(icons=tool_icons)
    async def get_ad_search(adsearch_id: int) -> dict:
        """Holt einen Suchauftrag anhand der ID."""
        client = _api_client(settings)
        return await _run_api(client.request("GET", f"/adsearches/{adsearch_id}"))

    @mcp.tool(icons=tool_icons)
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
        """Legt einen neuen Suchauftrag für eine Kleinanzeigen-Suchergebnis-URL an.

        Die Antwort enthält interne IDs nur für Folge-Tool-Aufrufe, nicht für Nutzerdialoge.
        """
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
        return await _run_api(client.request("POST", "/adsearches/", json_body=body))

    @mcp.tool(icons=tool_icons)
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
        return await _run_api(client.request("PATCH", f"/adsearches/{adsearch_id}", json_body=body))

    @mcp.tool(icons=tool_icons)
    async def delete_ad_search(adsearch_id: int) -> dict:
        """Löscht einen Suchauftrag inkl. zugehöriger Daten."""
        client = _api_client(settings)
        await _run_api(client.request("DELETE", f"/adsearches/{adsearch_id}"))
        return {"deleted": True, "adsearch_id": adsearch_id}

    register_mcp_apps(
        mcp,
        get_api_client=lambda: _api_client(settings),
        run_api=_run_api,
        tool_icons=tool_icons,
    )

    return mcp
