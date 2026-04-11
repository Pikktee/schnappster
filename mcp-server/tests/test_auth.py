"""Supabase token verifier."""

import httpx
import pytest

from schnappster_mcp.auth import SupabaseTokenVerifier


@pytest.mark.asyncio
async def test_verify_token_accepts_200(settings, respx_mock) -> None:
    respx_mock.get("https://test.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(200, json={"id": "u1", "email": "a@b.c"})
    )
    v = SupabaseTokenVerifier(settings)
    result = await v.verify_token("good-token")
    assert result is not None
    assert result.token == "good-token"
    assert result.scopes == []


@pytest.mark.asyncio
async def test_verify_token_rejects_401(settings, respx_mock) -> None:
    respx_mock.get("https://test.supabase.co/auth/v1/user").mock(
        return_value=httpx.Response(401)
    )
    v = SupabaseTokenVerifier(settings)
    assert await v.verify_token("bad") is None
