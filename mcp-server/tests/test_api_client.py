"""SchnappsterApiClient."""

import pytest

from schnappster_mcp.api_client import SchnappsterApiClient, SchnappsterApiError


@pytest.mark.asyncio
async def test_get_json(settings, httpx_mock) -> None:
    """Erfolgreicher GET liefert das dekodierte JSON-Objekt."""
    httpx_mock.add_response(
        url="http://test-api.local/ads/",
        method="GET",
        json={"items": [], "total": 0},
    )
    client = SchnappsterApiClient(settings, "tok")
    data = await client.request("GET", "/ads/")
    assert data == {"items": [], "total": 0}


@pytest.mark.asyncio
async def test_raises_on_error_detail(settings, httpx_mock) -> None:
    """Fehlerantwort mit FastAPI-``detail`` wird als ``SchnappsterApiError`` mit Text geworfen."""
    httpx_mock.add_response(
        url="http://test-api.local/x",
        method="GET",
        status_code=422,
        json={"detail": "nope"},
    )
    client = SchnappsterApiClient(settings, "tok")
    with pytest.raises(SchnappsterApiError) as ei:
        await client.request("GET", "/x")
    assert ei.value.status_code == 422
    assert "nope" in str(ei.value)
