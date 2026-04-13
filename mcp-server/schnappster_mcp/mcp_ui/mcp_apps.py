"""Eingebettete MCP-Apps (ext-apps): Schnäppchen-Detail, Liste, Suchaufträge."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Icon, TextContent

from schnappster_mcp.core.api_client import SchnappsterApiClient

from .template_render import render_mcp_app_html

_CDN_DOMAINS = ["https://unpkg.com"]


class _BaseMcpApp:
    """Gemeinsame Logik für alle eingebetteten MCP-Apps (ext-apps).

    Subklassen setzen nur ``VIEW_URI`` und ``_TEMPLATE``.
    """

    VIEW_URI: str
    MIME_TYPE: str = "text/html;profile=mcp-app"
    _TEMPLATE: str

    @classmethod
    def tool_meta(cls) -> dict[str, Any]:
        """Meta für MCP-Tools: verknüpft die eingebettete UI-Ressource (resourceUri)."""
        uri = cls.VIEW_URI
        return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}

    @classmethod
    def resource_meta(cls) -> dict[str, Any]:
        """Meta für die HTML-Ressource (CSP: erlaubte CDN-Domains für ext-apps)."""
        return {"ui": {"csp": {"resourceDomains": _CDN_DOMAINS}}}

    @classmethod
    def embedded_view_html(cls) -> str:
        """Gerendertes HTML+JS für diese MCP-App."""
        return render_mcp_app_html(cls._TEMPLATE)


class BargainDetailMcpApp(_BaseMcpApp):
    """Detailansicht für ein einzelnes Schnäppchen."""

    VIEW_URI = "ui://schnappster/bargain-detail.html"
    _TEMPLATE = "bargain_detail.html.j2"


class RecentBargainsMcpApp(_BaseMcpApp):
    """Tabellarische Übersicht für ``list_recent_bargains``."""

    VIEW_URI = "ui://schnappster/recent-bargains.html"
    _TEMPLATE = "recent_bargains.html.j2"


class AdSearchesMcpApp(_BaseMcpApp):
    """Verwaltung gespeicherter Suchaufträge via ``list_ad_searches``."""

    VIEW_URI = "ui://schnappster/ad-searches.html"
    _TEMPLATE = "ad_searches.html.j2"


def register_mcp_apps(
    mcp: FastMCP,
    *,
    get_api_client: Callable[[], SchnappsterApiClient],
    run_api: Callable[[Awaitable[Any]], Awaitable[Any]],
    tool_icons: list[Icon],
) -> None:
    """Registriert ``show_bargain_detail`` plus HTML-Ressourcen für eingebettete MCP-Apps."""

    @mcp.tool(
        icons=tool_icons,
        meta=BargainDetailMcpApp.tool_meta(),
        title="Schnäppchen-Details",
    )
    async def show_bargain_detail(ad_id: int) -> list[TextContent]:
        """Zeigt Details zu einer analysierten Anzeige in der MCP-App-Ansicht an.

        Parameter ``ad_id`` ist die interne Schnappster-Anzeigen-ID (z. B. aus
        ``list_recent_bargains``). Bei ext-app-fähigen Clients sollen Details primär über die
        Karte angezeigt werden und nicht als zusätzlicher langer Listen-/Tabellen-Text im Chat.
        """
        client = get_api_client()
        payload = await run_api(client.request("GET", f"/ads/{ad_id}"))
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return [TextContent(type="text", text=text)]

    for app_cls in (BargainDetailMcpApp, RecentBargainsMcpApp, AdSearchesMcpApp):
        _register_html_resource(mcp, app_cls)


def _register_html_resource(mcp: FastMCP, app_cls: type[_BaseMcpApp]) -> None:
    """Registriert eine einzelne HTML-Ressource für eine MCP-App-Klasse."""
    html = app_cls.embedded_view_html()

    @mcp.resource(
        app_cls.VIEW_URI,
        mime_type=app_cls.MIME_TYPE,
        meta=app_cls.resource_meta(),
    )
    def _view() -> str:
        return html
