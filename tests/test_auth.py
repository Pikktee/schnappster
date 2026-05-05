"""Tests fuer Supabase-Auth-Dependency."""

import pytest

from app.core import auth
from app.core.auth import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_caches_supabase_lookup(monkeypatch, httpx_mock):
    """Wiederholte API-Requests mit gleichem Token vermeiden erneute Supabase-Lookups."""
    auth._AUTH_CACHE.clear()
    monkeypatch.setattr(auth.config, "supabase_url", "https://test.supabase.co")
    monkeypatch.setattr(auth.config, "supabase_publishable_key", "publishable")
    monkeypatch.setattr(auth.config, "supabase_auth_cache_ttl", 60.0)
    monkeypatch.setattr(auth.config, "supabase_auth_timeout", 1.0)

    httpx_mock.add_response(
        url="https://test.supabase.co/auth/v1/user",
        json={
            "id": "user-1",
            "email": "test@example.com",
            "app_metadata": {"role": "user"},
            "user_metadata": {},
            "identities": [],
        },
    )

    first_user = await get_current_user("Bearer same-token")
    second_user = await get_current_user("Bearer same-token")

    assert first_user is second_user
    assert first_user.id == "user-1"
    assert len(httpx_mock.get_requests()) == 1

    auth._AUTH_CACHE.clear()
