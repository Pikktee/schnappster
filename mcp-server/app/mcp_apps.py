"""Eingebettete MCP-Apps (ext-apps): Schnäppchen-Detail, Liste, Suchaufträge."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Icon, TextContent

from schnappster_mcp.api_client import SchnappsterApiClient
from schnappster_mcp.mcp_ui_jinja import render_mcp_app_html


class BargainDetailMcpApp:
    """Detailansicht für ein einzelnes Schnäppchen."""

    VIEW_URI: str = "ui://schnappster/bargain-detail.html"
    MIME_TYPE: str = "text/html;profile=mcp-app"

    @classmethod
    def tool_meta(cls) -> dict[str, Any]:
        uri = cls.VIEW_URI
        return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}

    @classmethod
    def resource_meta(cls) -> dict[str, Any]:
        return {"ui": {"csp": {"resourceDomains": ["https://unpkg.com"]}}}

    @classmethod
    def embedded_view_html(cls) -> str:
        return render_mcp_app_html("bargain_detail.html.j2")


class RecentBargainsMcpApp:
    """Tabellarische Übersicht für ``list_recent_bargains``."""

    VIEW_URI: str = "ui://schnappster/recent-bargains.html"
    MIME_TYPE: str = "text/html;profile=mcp-app"

    @classmethod
    def tool_meta(cls) -> dict[str, Any]:
        uri = cls.VIEW_URI
        return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}

    @classmethod
    def resource_meta(cls) -> dict[str, Any]:
        return {"ui": {"csp": {"resourceDomains": ["https://unpkg.com"]}}}

    @classmethod
    def embedded_view_html(cls) -> str:
        return render_mcp_app_html("recent_bargains.html.j2")


class AdSearchesMcpApp:
    """Verwaltung gespeicherter Suchaufträge via ``list_ad_searches``."""

    VIEW_URI: str = "ui://schnappster/ad-searches.html"
    MIME_TYPE: str = "text/html;profile=mcp-app"

    @classmethod
    def tool_meta(cls) -> dict[str, Any]:
        uri = cls.VIEW_URI
        return {"ui": {"resourceUri": uri}, "ui/resourceUri": uri}

    @classmethod
    def resource_meta(cls) -> dict[str, Any]:
        return {"ui": {"csp": {"resourceDomains": ["https://unpkg.com"]}}}

    @classmethod
    def embedded_view_html(cls) -> str:
        return render_mcp_app_html("ad_searches.html.j2")


def recent_bargains_tool_meta() -> dict[str, Any]:
    """Meta-Konfiguration für ``list_recent_bargains``."""
    return RecentBargainsMcpApp.tool_meta()


def ad_searches_tool_meta() -> dict[str, Any]:
    """Meta-Konfiguration für ``list_ad_searches``."""
    return AdSearchesMcpApp.tool_meta()


def register_mcp_apps(
    mcp: FastMCP,
    *,
    get_api_client: Callable[[], SchnappsterApiClient],
    run_api: Callable[[Awaitable[Any]], Awaitable[Any]],
    tool_icons: list[Icon],
) -> None:
    """Registriert ``show_bargain_detail`` und die zugehörigen UI-Ressourcen."""

    app = BargainDetailMcpApp

    @mcp.tool(
        icons=tool_icons,
        meta=app.tool_meta(),
        title="Schnäppchen-Details",
    )
    async def show_bargain_detail(ad_id: int) -> list[TextContent]:
        """Zeigt Details zu einer analysierten Anzeige in der MCP-App-Ansicht an.

        Parameter ``ad_id`` ist die interne Schnappster-Anzeigen-ID (z. B. aus
        ``list_recent_bargains``).
        """
        client = get_api_client()
        payload = await run_api(client.request("GET", f"/ads/{ad_id}"))
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return [TextContent(type="text", text=text)]

    @mcp.resource(
        app.VIEW_URI,
        mime_type=app.MIME_TYPE,
        meta=app.resource_meta(),
    )
    def bargain_detail_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für die Detailansicht."""
        return app.embedded_view_html()

    recent_bargains = RecentBargainsMcpApp

    @mcp.resource(
        recent_bargains.VIEW_URI,
        mime_type=recent_bargains.MIME_TYPE,
        meta=recent_bargains.resource_meta(),
    )
    def recent_bargains_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für list_recent_bargains."""
        return recent_bargains.embedded_view_html()

    ad_searches = AdSearchesMcpApp

    @mcp.resource(
        ad_searches.VIEW_URI,
        mime_type=ad_searches.MIME_TYPE,
        meta=ad_searches.resource_meta(),
    )
    def ad_searches_view() -> str:
        """Gebündelte MCP-App (HTML+JS) für list_ad_searches."""
        return ad_searches.embedded_view_html()
