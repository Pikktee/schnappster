"""FastMCP app: Streamable HTTP, Schnappster JWT auth, Schnappster API tools."""

import base64
import html
from collections.abc import Awaitable
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal
from urllib.parse import urlparse

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import Icon
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from schnappster_mcp.core.api_client import SchnappsterApiClient, SchnappsterApiError
from schnappster_mcp.core.config import Settings
from schnappster_mcp.core.oauth_provider import LoginError, SchnappsterOAuthProvider
from schnappster_mcp.mcp_ui.mcp_apps import (
    AdSearchesMcpApp,
    RecentBargainsMcpApp,
    register_mcp_apps,
)

_FAVICON_CACHE_CONTROL_MAX_AGE_S = 86400
_SETTINGS_FIELDS_HIDDEN_FROM_LLM = frozenset({"deletion_pending"})


def build_mcp(settings: Settings) -> FastMCP:
    """Baut die FastMCP-Instanz inkl. Auth, Tools, Health- und Branding-Routen."""
    resource = settings.mcp_resource_server_url
    assert resource is not None

    # Pro Tool in tools/list — viele Clients (z. B. Claude „Tool Use“) nutzen diese Felder,
    # nicht nur serverInfo.icons aus initialize.
    tool_icons = _schnappster_mcp_icons()

    # Der mcp-server ist selbst der OAuth-Authorization-Server (DCR + Login-Seite + Token).
    oauth_provider = SchnappsterOAuthProvider(settings)

    mcp = FastMCP(
        name="Schnappster",
        instructions=(
            "Zugriff auf Schnappster: Schnäppchen (Ads mit Score), persönliche "
            "Benutzereinstellungen und Suchaufträge (Ad Searches). "
            "Authentifizierung: Schnappster Access Token als Bearer (nach Login im Web-Frontend). "
            "In Antworten an Endnutzer keine internen numerischen IDs (z. B. von Anzeigen "
            "oder Suchaufträgen) nennen; stattdessen Titel, Name des Suchauftrags oder "
            "Kurzbeschreibung verwenden. IDs nur still für Folge-Tool-Aufrufe nutzen. "
            "MCP-Apps (eingebettete Oberfläche bei list_recent_bargains, list_ad_searches, "
            "show_bargain_detail): Vor dem Tool-Aufruf höchstens 1 kurzer Einordnungssatz. "
            "Rufe das Tool direkt danach auf. Nach dem Tool-Aufruf keine zusätzliche "
            "Auflistung als Tabelle, Bullet-Liste oder Wiederholung der einzelnen Treffer im "
            "Chat ausgeben; die eigentliche Darstellung erfolgt in der App. Wenn nötig, nur "
            "eine knappe Ein-Satz-Zusammenfassung ohne Einzelposten. Für Details zu einer "
            "Anzeige: show_bargain_detail (falls der Client ext-apps unterstützt)."
        ),
        icons=tool_icons,
        json_response=True,
        # Keine serverseitige MCP-Session: vermeidet „session … no longer exists“ bei
        # Deploys, mehreren Instanzen, Tunnel-Reconnects und längeren Client-Pausen.
        stateless_http=True,
        auth_server_provider=oauth_provider,
        auth=AuthSettings(
            # Issuer = der mcp-server selbst; /authorize, /token, /register und die
            # AS-Metadata liegen hier. Tokens werden gegen GET /users/me/ validiert.
            issuer_url=AnyHttpUrl(settings.mcp_issuer_url),
            resource_server_url=resource,
            required_scopes=None,
            client_registration_options=ClientRegistrationOptions(enabled=True),
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

    @mcp.custom_route("/oauth/login", methods=["GET"])
    async def oauth_login_form(request: Request) -> Response:
        """Login-Seite des OAuth-Flows: zeigt das E-Mail/Passwort-Formular."""
        txn = request.query_params.get("txn", "")
        return HTMLResponse(_login_page_html(txn))

    @mcp.custom_route("/oauth/login", methods=["POST"])
    async def oauth_login_submit(request: Request) -> Response:
        """Prüft die Anmeldedaten und leitet bei Erfolg zum OAuth-Client zurück."""
        form = await request.form()
        txn = str(form.get("txn", ""))
        email = str(form.get("email", "")).strip()
        password = str(form.get("password", ""))
        try:
            redirect_url = await oauth_provider.complete_login(txn, email, password)
        except LoginError as exc:
            return HTMLResponse(_login_page_html(txn, error=str(exc)), status_code=401)
        return RedirectResponse(redirect_url, status_code=302)

    @mcp.tool(icons=tool_icons, meta=RecentBargainsMcpApp.tool_meta())
    async def list_recent_bargains(
        limit: int = 24,
        offset: int = 0,
        min_score: int | None = None,
        adsearch_id: int | None = None,
    ) -> dict:
        """Listet analysierte Anzeigen, sortiert nach Schnäppchen-Score (höchste zuerst).

        Bei Clients mit MCP-App soll die Ergebnisliste nur in der App angezeigt werden, nicht
        zusätzlich als Tabelle oder Bullet-Liste im Chat-Text.
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
        result = await _run_api(client.request("GET", "/ads/", params=params))
        # Konsistentes Format: immer {items, total} — unabhängig vom API-Rückgabeformat.
        if isinstance(result, list):
            return {"items": result, "total": len(result)}
        if isinstance(result, dict) and "items" in result:
            return result
        return {"items": [], "total": 0}

    @mcp.tool(icons=tool_icons)
    async def get_my_settings() -> dict:
        """Liest persönliche Benutzereinstellungen (Benachrichtigungen, Telegram, Mindest-Score)."""
        client = _api_client(settings)
        payload = await _run_api(client.request("GET", "/users/me/settings"))
        return _sanitize_user_settings(payload) if isinstance(payload, dict) else payload

    @mcp.tool(icons=tool_icons)
    async def update_my_settings(
        display_name: str | None = None,
        telegram_chat_id: str | None = None,
        notify_telegram: bool | None = None,
        notify_min_score: int | None = None,
    ) -> dict:
        """Aktualisiert persönliche Einstellungen (nur angegebene Felder)."""
        body = _collect_set_fields(
            display_name=display_name,
            telegram_chat_id=telegram_chat_id,
            notify_telegram=notify_telegram,
            notify_min_score=notify_min_score,
        )
        if not body:
            raise ToolError("Mindestens ein Feld zum Aktualisieren angeben.")
        client = _api_client(settings)
        payload = await _run_api(client.request("PATCH", "/users/me/settings", json_body=body))
        return _sanitize_user_settings(payload) if isinstance(payload, dict) else payload

    @mcp.tool(icons=tool_icons, meta=AdSearchesMcpApp.tool_meta())
    async def list_ad_searches() -> dict:
        """Listet alle Suchaufträge; Antwort als Objekt mit ``items`` (kein Top-Level-Array).

        Bei Clients mit MCP-App soll die Ergebnisliste nur in der App angezeigt werden, nicht
        zusätzlich als Tabelle oder Bullet-Liste im Chat-Text.
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
        body = _collect_set_fields(
            name=name,
            url=url,
            prompt_addition=prompt_addition,
            min_price=min_price,
            max_price=max_price,
            blacklist_keywords=blacklist_keywords,
            is_exclude_images=is_exclude_images,
            is_active=is_active,
            scrape_interval_minutes=scrape_interval_minutes,
        )
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


def _login_page_html(txn: str, error: str | None = None) -> str:
    """Rendert die minimalistische OAuth-Login-Seite (E-Mail/Passwort, Schnappster-Branding)."""
    error_block = (
        f'<p class="error">{html.escape(error)}</p>' if error else ""
    )
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Schnappster – Anmelden</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         display: grid; place-items: center; min-height: 100vh; margin: 0;
         background: #0f0f0f; color: #f5f5f5; }}
  .card {{ width: min(360px, 92vw); background: #1b1b1b; border: 1px solid #2c2c2c;
          border-radius: 16px; padding: 32px; box-shadow: 0 10px 40px rgba(0,0,0,.4); }}
  .brand {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
  .brand img {{ width: 36px; height: 36px; border-radius: 8px; }}
  .brand h1 {{ font-size: 1.15rem; margin: 0; }}
  label {{ display: block; font-size: .85rem; margin: 14px 0 6px; color: #bdbdbd; }}
  input {{ width: 100%; box-sizing: border-box; padding: 11px 12px; border-radius: 9px;
          border: 1px solid #3a3a3a; background: #111; color: #fff; font-size: 1rem; }}
  input:focus {{ outline: 2px solid #e0a106; border-color: transparent; }}
  button {{ width: 100%; margin-top: 22px; padding: 12px; border: 0; border-radius: 9px;
           background: #e0a106; color: #1a1a1a; font-weight: 600; font-size: 1rem;
           cursor: pointer; }}
  button:hover {{ background: #f0b418; }}
  .error {{ background: #3a1414; border: 1px solid #6b2020; color: #ffb4b4;
           padding: 10px 12px; border-radius: 9px; font-size: .9rem; margin: 0 0 4px; }}
  .hint {{ color: #888; font-size: .8rem; margin-top: 18px; text-align: center; }}
</style>
</head>
<body>
  <form class="card" method="post" action="/oauth/login">
    <div class="brand">
      <img src="/icon.png" alt="Schnappster">
      <h1>Mit Schnappster verbinden</h1>
    </div>
    {error_block}
    <input type="hidden" name="txn" value="{html.escape(txn)}">
    <label for="email">E-Mail</label>
    <input id="email" name="email" type="email" autocomplete="username" required autofocus>
    <label for="password">Passwort</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Anmelden &amp; verbinden</button>
    <p class="hint">Zugriff für den Schnappster Remote-MCP-Server.</p>
  </form>
</body>
</html>"""


@lru_cache(maxsize=1)
def _schnappster_mcp_icon_png_bytes() -> bytes:
    """PNG-Rohbytes für MCP-Icons und Favicon-Routen (wie ``web/app/icon.png``)."""
    return files("schnappster_mcp").joinpath("assets", "icon.png").read_bytes()


def _collect_set_fields(**kwargs: Any) -> dict[str, Any]:
    """Sammelt nur die Keyword-Argumente, die nicht ``None`` sind (für PATCH-Bodys)."""
    return {k: v for k, v in kwargs.items() if v is not None}


async def _run_api[T](coro: Awaitable[T]) -> T:
    """Wartet auf ``coro`` und wandelt ``SchnappsterApiError`` in ``ToolError`` um."""
    try:
        return await coro
    except SchnappsterApiError as exc:
        raise ToolError(f"Schnappster-API ({exc.status_code}): {exc}") from exc


def _sanitize_user_settings(payload: dict) -> dict:
    """Entfernt nicht relevante interne Settings-Felder aus MCP-Tool-Antworten."""
    return {
        key: value for key, value in payload.items() if key not in _SETTINGS_FIELDS_HIDDEN_FROM_LLM
    }


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
            "Nicht authentifiziert: gültiges Bearer-Token (Schnappster Access Token) erforderlich."
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
