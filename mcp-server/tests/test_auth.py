"""Supabase token verifier."""

import pytest

from schnappster_mcp.core.auth import SupabaseTokenVerifier


@pytest.mark.asyncio
async def test_verify_token_accepts_200(settings, httpx_mock) -> None:
    """Bei HTTP 200 liefert der Verifier einen ``AccessToken`` mit dem übergebenen Token."""
    httpx_mock.add_response(
        url="https://test.supabase.co/auth/v1/user",
        method="GET",
        json={"id": "u1", "email": "a@b.c"},
    )
    v = SupabaseTokenVerifier(settings)
    result = await v.verify_token("good-token")
    assert result is not None
    assert result.token == "good-token"
    assert result.scopes == []


@pytest.mark.asyncio
async def test_verify_token_rejects_401(settings, httpx_mock) -> None:
    """Bei HTTP 401 gibt ``verify_token`` ``None`` zurück."""
    httpx_mock.add_response(
        url="https://test.supabase.co/auth/v1/user",
        method="GET",
        status_code=401,
    )
    v = SupabaseTokenVerifier(settings)
    assert await v.verify_token("bad") is None
