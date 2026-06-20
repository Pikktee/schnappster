"""Schnappster-API token verifier."""

import pytest

from schnappster_mcp.core.auth import ApiTokenVerifier


@pytest.mark.asyncio
async def test_verify_token_accepts_200(settings, httpx_mock) -> None:
    """Bei HTTP 200 liefert der Verifier einen ``AccessToken`` mit dem übergebenen Token."""
    httpx_mock.add_response(
        url="http://test-api.local/users/me/",
        method="GET",
        json={"id": "u1", "email": "a@b.c", "role": "user"},
    )
    v = ApiTokenVerifier(settings)
    result = await v.verify_token("good-token")
    assert result is not None
    assert result.token == "good-token"
    assert result.client_id == "u1"
    assert result.scopes == []


@pytest.mark.asyncio
async def test_verify_token_rejects_401(settings, httpx_mock) -> None:
    """Bei HTTP 401 gibt ``verify_token`` ``None`` zurück."""
    httpx_mock.add_response(
        url="http://test-api.local/users/me/",
        method="GET",
        status_code=401,
    )
    v = ApiTokenVerifier(settings)
    assert await v.verify_token("bad") is None
