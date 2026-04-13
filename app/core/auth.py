"""Supabase-basierte Auth-Dependencies fuer FastAPI."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.core.config import config
from app.core.request_context import get_http_request_trace_id

_log = logging.getLogger("schnappster.auth")

# Shared httpx-Client: verhindert, dass pro Request ein neuer TCP-Handshake + TLS-Aufbau noetig ist.
# Wird beim ersten Aufruf von get_current_user erstellt (Lazy-Init).
_auth_http_client: httpx.AsyncClient | None = None


def _get_auth_http_client() -> httpx.AsyncClient:
    global _auth_http_client  # noqa: PLW0603
    if _auth_http_client is None:
        _auth_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=6.0),
            limits=httpx.Limits(max_connections=24, max_keepalive_connections=8),
        )
    return _auth_http_client


async def close_auth_http_client() -> None:
    """Shutdown-Hook: schliesst den shared httpx-Client."""
    global _auth_http_client  # noqa: PLW0603
    if _auth_http_client is not None:
        await _auth_http_client.aclose()
        _auth_http_client = None


# --- Auth-Cache: identischer Token wird nicht mehrfach bei Supabase validiert. ---
# Parallele Requests vom selben Seitenwechsel teilen sich eine einzige Validierung.
_auth_cache: dict[str, tuple[CurrentUser, float]] = {}
_auth_inflight: dict[str, asyncio.Future[CurrentUser]] = {}
# Ohne Lock koennen zwei Coroutines gleichzeitig "inflight leer" sehen, zwei Futures
# registrieren (Ueberschreiben) und auf einem nie gesetzten Future awaiten -> Haenger.
_auth_inflight_lock = asyncio.Lock()


def _auth_token_fingerprint(access_token: str) -> str:
    return hashlib.sha256(access_token.encode("utf-8")).hexdigest()[:10]


def _auth_trace(message: str) -> None:
    if _log.isEnabledFor(logging.DEBUG):
        rid = get_http_request_trace_id() or "-"
        _log.debug("[%s] auth %s", rid, message)


def _get_cached_user(token: str) -> CurrentUser | None:
    entry = _auth_cache.get(token)
    if entry and (time.monotonic() - entry[1]) < config.auth_user_cache_ttl_seconds:
        return entry[0]
    _auth_cache.pop(token, None)
    return None


def _set_cached_user(token: str, user: CurrentUser) -> None:
    _auth_cache[token] = (user, time.monotonic())
    # Begrenzte Cache-Groesse: aelteste Eintraege entfernen
    if len(_auth_cache) > config.auth_user_cache_max_entries:
        cutoff = time.monotonic() - config.auth_user_cache_ttl_seconds
        expired = [k for k, (_, ts) in _auth_cache.items() if ts < cutoff]
        for k in expired:
            _auth_cache.pop(k, None)
        # Falls keine Expired-Einträge vorhanden sind: zufällige ältere Items trimmen.
        if len(_auth_cache) > config.auth_user_cache_max_entries:
            overflow = len(_auth_cache) - config.auth_user_cache_max_entries
            for key in list(_auth_cache.keys())[:overflow]:
                _auth_cache.pop(key, None)


def _jwt_sub_from_access_token(access_token: str) -> str | None:
    """Liest `sub` aus dem JWT-Payload (ohne Signaturpruefung — Token ist via /user validiert)."""
    try:
        parts = access_token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        pad = (-len(payload_b64)) % 4
        if pad:
            payload_b64 += "=" * pad
        raw = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        sub = payload.get("sub")
        return str(sub).strip() if sub else None
    except (ValueError, json.JSONDecodeError, binascii.Error, UnicodeDecodeError):
        return None


@dataclass(slots=True)
class CurrentUser:
    """Minimales User-Objekt aus dem Supabase-Auth-User-Endpunkt."""

    id: str
    email: str | None
    app_metadata: dict[str, Any]
    user_metadata: dict[str, Any]
    identities: list[dict[str, Any]]
    access_token: str

    @property
    def user_id(self) -> str:
        """User-ID fuer Postgres/RLS: immer `sub` aus dem Access-Token, sonst User-API-`id`."""
        sub = _jwt_sub_from_access_token(self.access_token)
        return sub if sub else self.id

    @property
    def role(self) -> str:
        """Rolle aus app_metadata oder Fallback 'user'."""
        return str(self.app_metadata.get("role", "user"))


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return parts[1].strip()


def _require_supabase_auth_config() -> None:
    if not config.supabase_url or not config.supabase_publishable_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth is not configured on the server",
        )


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Validiert Bearer-Token ueber Supabase und liefert User-Claims.

    Cache + Request-Dedup: parallele Requests mit identischem Token teilen
    sich eine einzige Supabase-Validierung (wichtig bei Seitenwechseln, die
    4+ API-Calls gleichzeitig ausloesen).
    """
    _require_supabase_auth_config()
    access_token = _extract_bearer_token(authorization)
    _auth_trace(f"begin token_fp={_auth_token_fingerprint(access_token)}")

    # 1. Cache-Hit? (ohne Lock — nur lesen; veralteter Eintrag ok)
    cached = _get_cached_user(access_token)
    if cached is not None:
        _auth_trace("cache hit")
        return cached

    loop = asyncio.get_running_loop()
    is_leader = False
    future: asyncio.Future[CurrentUser]

    async with _auth_inflight_lock:
        cached = _get_cached_user(access_token)
        if cached is not None:
            _auth_trace("cache hit (after lock)")
            return cached
        existing = _auth_inflight.get(access_token)
        if existing is not None:
            future = existing
            _auth_trace("await inflight future")
        else:
            future = loop.create_future()
            _auth_inflight[access_token] = future
            is_leader = True
            _auth_trace("registered inflight leader")

    if not is_leader:
        _auth_trace("follower await inflight start")
        try:
            return await future
        finally:
            _auth_trace("follower await inflight done")

    try:
        _auth_trace("validate start")
        user = await asyncio.wait_for(
            _validate_token_at_supabase(access_token),
            timeout=15.0,
        )
        _auth_trace("validate ok")
        _set_cached_user(access_token, user)
        if not future.done():
            future.set_result(user)
        return user
    except TimeoutError as exc:
        he = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth validation timed out — check SUPABASE_URL/network",
        )
        if not future.done():
            future.set_exception(he)
        raise he from exc
    except BaseException as exc:
        if not future.done():
            future.set_exception(exc)
        raise
    finally:
        async with _auth_inflight_lock:
            _auth_inflight.pop(access_token, None)
        _auth_trace("inflight cleared")


async def _validate_token_at_supabase(access_token: str) -> CurrentUser:
    """Einmaliger HTTP-Call zu Supabase Auth /user."""
    url = f"{config.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": config.supabase_publishable_key,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        client = _get_auth_http_client()
        _auth_trace("supabase GET /auth/v1/user start")
        response = await client.get(url, headers=headers)
        _auth_trace(f"supabase GET /auth/v1/user done status={response.status_code}")
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Auth upstream unavailable: {exc}",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    data = response.json()
    raw_identities = data.get("identities")
    identities: list[dict[str, Any]] = raw_identities if isinstance(raw_identities, list) else []
    return CurrentUser(
        id=str(data.get("id", "")),
        email=data.get("email"),
        app_metadata=data.get("app_metadata") or {},
        user_metadata=data.get("user_metadata") or {},
        identities=identities,
        access_token=access_token,
    )


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:  # noqa: B008
    """Erlaubt Zugriff nur fuer Admin-Rolle."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def display_name_from_identity_metadata(meta: dict[str, Any]) -> str:
    """Liest einen Anzeigenamen aus user_metadata bzw. Supabase identity_data (z. B. Google)."""
    if not meta:
        return ""
    for key in ("full_name", "name", "preferred_username", "nickname"):
        v = meta.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    given = meta.get("given_name")
    family = meta.get("family_name")
    parts: list[str] = []
    if isinstance(given, str) and given.strip():
        parts.append(given.strip())
    if isinstance(family, str) and family.strip():
        parts.append(family.strip())
    if parts:
        return " ".join(parts)
    return ""


def identity_display_name(user: CurrentUser) -> str:
    """Bester verfuegbarer Anzeigename aus user_metadata und OAuth-Identities."""
    n = display_name_from_identity_metadata(user.user_metadata or {})
    if n:
        return n
    for ident in user.identities:
        if not isinstance(ident, dict):
            continue
        idata = ident.get("identity_data")
        if isinstance(idata, dict):
            n = display_name_from_identity_metadata(idata)
            if n:
                return n
    return ""
