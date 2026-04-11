"""SchnappsterApiClient."""

import httpx
import pytest

from schnappster_mcp.api_client import SchnappsterApiClient, SchnappsterApiError


@pytest.mark.asyncio
async def test_get_json(settings, respx_mock) -> None:
    respx_mock.get("http://test-api.local/ads/").mock(
        return_value=httpx.Response(200, json={"items": [], "total": 0})
    )
    client = SchnappsterApiClient(settings, "tok")
    data = await client.request("GET", "/ads/")
    assert data == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_raises_on_error_detail(settings, respx_mock) -> None:
    respx_mock.get("http://test-api.local/x").mock(
        return_value=httpx.Response(422, json={"detail": "nope"})
    )
    client = SchnappsterApiClient(settings, "tok")
    with pytest.raises(SchnappsterApiError) as ei:
        await client.request("GET", "/x")
    assert ei.value.status_code == 422
    assert "nope" in str(ei.value)
