"""Tests für die MCP-App „Schnäppchen-Details“."""

from typing import Any, cast

import pytest
from mcp.server.fastmcp import FastMCP

from schnappster_mcp.api_client import SchnappsterApiClient
from schnappster_mcp.bargain_detail_app import BargainDetailMcpApp, register_bargain_detail_mcp_app


class _FakeApiClient:
    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
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
    mcp = FastMCP("test-mcp", json_response=True)

    async def run_api(coro: Any) -> Any:
        return await coro

    register_bargain_detail_mcp_app(
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
    meta = BargainDetailMcpApp.tool_meta()
    assert meta["ui"]["resourceUri"] == BargainDetailMcpApp.VIEW_URI
    assert meta["ui/resourceUri"] == BargainDetailMcpApp.VIEW_URI


def test_embedded_view_includes_app_bridge_import() -> None:
    html = BargainDetailMcpApp.embedded_view_html()
    assert "unpkg.com" in html
    assert "@modelcontextprotocol/ext-apps" in html
    assert "ontoolresult" in html
