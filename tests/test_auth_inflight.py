"""Tests fuer Auth-Inflight-Deduplizierung (Race ohne Lock = Haenger)."""

from __future__ import annotations

import asyncio
import base64
import json
from types import SimpleNamespace

import pytest

from app.core.auth import CurrentUser, get_current_user


def _minimal_bearer_jwt(sub: str = "test-sub-uuid") -> str:
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )
    return f"a.{payload}.c"


@pytest.mark.asyncio
async def test_parallel_same_token_single_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.auth as auth_mod

    auth_mod._auth_cache.clear()
    auth_mod._auth_inflight.clear()
    monkeypatch.setattr(
        auth_mod,
        "config",
        SimpleNamespace(
            supabase_url="https://unit-test.supabase.co",
            supabase_publishable_key="pk",
            auth_user_cache_ttl_seconds=120,
            auth_user_cache_max_entries=500,
        ),
    )

    calls = {"n": 0}
    token = _minimal_bearer_jwt()

    async def fake_validate(access_token: str) -> CurrentUser:
        calls["n"] += 1
        await asyncio.sleep(0.1)
        assert access_token == token
        return CurrentUser(
            id="id-from-api",
            email="t@t.de",
            app_metadata={"role": "authenticated"},
            user_metadata={},
            identities=[],
            access_token=access_token,
        )

    monkeypatch.setattr(auth_mod, "_validate_token_at_supabase", fake_validate)

    async def one() -> CurrentUser:
        return await get_current_user(f"Bearer {token}")

    results = await asyncio.gather(*(one() for _ in range(12)))
    assert calls["n"] == 1
    assert all(r.user_id == results[0].user_id for r in results)

    auth_mod._auth_cache.clear()
    auth_mod._auth_inflight.clear()
