"""Öffentliche Branding-Routen (Favicon) für MCP-Connector-URLs."""

import httpx
import pytest

from schnappster_mcp.server import build_mcp


@pytest.mark.parametrize(
    "path",
    ["/favicon.ico", "/apple-touch-icon.png", "/icon.png"],
)
@pytest.mark.asyncio
async def test_branding_png_routes_return_png(settings, path: str) -> None:
    """Branding-Pfade liefern PNG mit passendem Content-Type und Cache-Control."""
    mcp = build_mcp(settings)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("image/png")
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "max-age=86400" in response.headers.get("cache-control", "")
