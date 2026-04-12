"""Tests für eingebettete MCP-Apps (ext-apps)."""

from typing import Any, cast

import pytest
from mcp.server.fastmcp import FastMCP

from schnappster_mcp.core.api_client import SchnappsterApiClient
from schnappster_mcp.mcp_ui.mcp_apps import BargainDetailMcpApp, register_mcp_apps


class _FakeApiClient:
    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Stub: liefert feste Anzeigendaten für ``GET /ads/7``."""
        assert method == "GET"
        assert path == "/ads/7"
        return {
            "id": 7,
            "title": "Beispiel-Stuhl",
            "bargain_score": 9,
            "url": "https://www.kleinanzeigen.de/s-anzeige/example-7",
            "ai_summary": "Guter Deal.",
            "city": "Berlin",
        }


@pytest.mark.asyncio
async def test_show_bargain_detail_tool_and_resource_registered() -> None:
    """``register_mcp_apps`` registriert Tool, Resource-URI und liefert JSON mit Anzeigentitel."""
    mcp = FastMCP("test-mcp", json_response=True)

    async def run_api(coro: Any) -> Any:
        """Führt die übergebene Coroutine ohne Wrapper aus."""
        return await coro

    register_mcp_apps(
        mcp,
        get_api_client=lambda: cast(SchnappsterApiClient, _FakeApiClient()),
        run_api=run_api,
        tool_icons=[],
    )

    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    assert "show_bargain_detail" in by_name
    meta = by_name["show_bargain_detail"].meta
    assert meta is not None
    assert meta["ui"]["resourceUri"] == BargainDetailMcpApp.VIEW_URI

    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert BargainDetailMcpApp.VIEW_URI in uris

    out = await mcp.call_tool("show_bargain_detail", {"ad_id": 7})
    assert out is not None
    # FastMCP wandelt list[TextContent] in ContentBlocks um
    text_joined = str(out)
    assert "Beispiel-Stuhl" in text_joined


def test_tool_meta_shape() -> None:
    """``tool_meta`` enthält konsistente ``resourceUri``-Felder."""
    meta = BargainDetailMcpApp.tool_meta()
    assert meta["ui"]["resourceUri"] == BargainDetailMcpApp.VIEW_URI
    assert meta["ui/resourceUri"] == BargainDetailMcpApp.VIEW_URI


def test_embedded_view_includes_app_bridge_import() -> None:
    """Eingebettetes HTML bindet ext-apps von unpkg und enthält Event-Handler-Namen."""
    html = BargainDetailMcpApp.embedded_view_html()
    assert "unpkg.com" in html
    assert "@modelcontextprotocol/ext-apps" in html
    assert "ontoolresult" in html
    assert "resolvePrimaryImage" in html
    assert "Mehr anzeigen" in html
