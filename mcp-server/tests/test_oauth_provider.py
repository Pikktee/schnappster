"""OAuth-Provider: DCR, Login gegen die API, Code->Token-Tausch, Token-Validierung."""

import base64
import json
import time
from urllib.parse import parse_qs, urlparse

import pytest
from mcp.server.auth.provider import AuthorizationParams, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from schnappster_mcp.core.oauth_provider import (
    LoginError,
    SchnappsterOAuthProvider,
    _jwt_seconds_until_expiry,
)

REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"
LOGIN_URL = "http://test-api.local/auth/login"
USERS_ME_URL = "http://test-api.local/users/me/"


def _fake_jwt(exp: int) -> str:
    """Baut ein JWT-aehnliches Token mit ``exp`` (nur fuer Parsing-Tests, ohne Signatur)."""
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=")
    return f"header.{payload.decode()}.sig"


def _client() -> OAuthClientInformationFull:
    """Minimaler registrierbarer Client mit gueltiger Redirect-URI."""
    return OAuthClientInformationFull(
        client_id="client-1",
        client_secret="secret",
        redirect_uris=[AnyUrl(REDIRECT_URI)],
    )


def _params(state: str | None = "xyz") -> AuthorizationParams:
    """Authorization-Parameter wie sie der ``/authorize``-Handler uebergeben wuerde."""
    return AuthorizationParams(
        state=state,
        scopes=[],
        code_challenge="challenge",
        redirect_uri=AnyUrl(REDIRECT_URI),
        redirect_uri_provided_explicitly=True,
        resource="https://mcp.test/",
    )


async def _txn_for(provider: SchnappsterOAuthProvider) -> str:
    """Registriert den Client, ruft ``authorize`` auf und liefert die Login-Transaktion."""
    client = _client()
    await provider.register_client(client)
    redirect = await provider.authorize(client, _params())
    return parse_qs(urlparse(redirect).query)["txn"][0]


async def test_register_and_get_client(settings) -> None:
    """Ein registrierter Client ist anschliessend ueber ``get_client`` abrufbar."""
    provider = SchnappsterOAuthProvider(settings)
    client = _client()
    await provider.register_client(client)
    assert (await provider.get_client("client-1")) is client
    assert (await provider.get_client("unknown")) is None


async def test_authorize_redirects_to_login_page(settings) -> None:
    """``authorize`` leitet auf die Login-Seite des Issuers mit einer ``txn`` um."""
    provider = SchnappsterOAuthProvider(settings)
    client = _client()
    await provider.register_client(client)
    redirect = await provider.authorize(client, _params())
    parsed = urlparse(redirect)
    assert parsed.path == "/oauth/login"
    assert redirect.startswith(settings.mcp_issuer_url)
    assert "txn" in parse_qs(parsed.query)


async def test_complete_login_success_issues_code_and_token(settings, httpx_mock) -> None:
    """Erfolgreicher Login erzeugt einen Code, der gegen das App-JWT getauscht wird."""
    token = _fake_jwt(int(time.time()) + 3600)
    httpx_mock.add_response(
        url=LOGIN_URL, method="POST", json={"access_token": token, "token_type": "bearer"}
    )
    provider = SchnappsterOAuthProvider(settings)
    txn = await _txn_for(provider)

    redirect = await provider.complete_login(txn, "a@b.c", "pw")
    query = parse_qs(urlparse(redirect).query)
    assert query["state"] == ["xyz"]
    code = query["code"][0]

    client = await provider.get_client("client-1")
    loaded = await provider.load_authorization_code(client, code)
    assert loaded is not None and loaded.app_jwt == token

    oauth_token = await provider.exchange_authorization_code(client, loaded)
    assert oauth_token.access_token == token
    assert oauth_token.expires_in is not None and oauth_token.expires_in > 0


async def test_authorization_code_is_single_use(settings, httpx_mock) -> None:
    """Nach dem ersten Tausch ist der Code verbraucht (zweiter Tausch schlaegt fehl)."""
    httpx_mock.add_response(
        url=LOGIN_URL, method="POST", json={"access_token": _fake_jwt(int(time.time()) + 60)}
    )
    provider = SchnappsterOAuthProvider(settings)
    txn = await _txn_for(provider)
    redirect = await provider.complete_login(txn, "a@b.c", "pw")
    code = parse_qs(urlparse(redirect).query)["code"][0]
    client = await provider.get_client("client-1")

    loaded = await provider.load_authorization_code(client, code)
    await provider.exchange_authorization_code(client, loaded)
    assert (await provider.load_authorization_code(client, code)) is None
    with pytest.raises(TokenError):
        await provider.exchange_authorization_code(client, loaded)


async def test_complete_login_wrong_credentials(settings, httpx_mock) -> None:
    """HTTP 401 vom Login-Endpoint fuehrt zu einer ``LoginError`` (falsche Daten)."""
    httpx_mock.add_response(url=LOGIN_URL, method="POST", status_code=401)
    provider = SchnappsterOAuthProvider(settings)
    txn = await _txn_for(provider)
    with pytest.raises(LoginError, match="Passwort"):
        await provider.complete_login(txn, "a@b.c", "wrong")


async def test_complete_login_inactive_account(settings, httpx_mock) -> None:
    """HTTP 403 (nicht freigeschaltet) erzeugt eine passende ``LoginError``."""
    httpx_mock.add_response(url=LOGIN_URL, method="POST", status_code=403)
    provider = SchnappsterOAuthProvider(settings)
    txn = await _txn_for(provider)
    with pytest.raises(LoginError, match="freigeschaltet"):
        await provider.complete_login(txn, "a@b.c", "pw")


async def test_complete_login_unknown_txn(settings) -> None:
    """Eine unbekannte/abgelaufene Transaktion fuehrt zu ``LoginError``."""
    provider = SchnappsterOAuthProvider(settings)
    with pytest.raises(LoginError, match="abgelaufen"):
        await provider.complete_login("nope", "a@b.c", "pw")


async def test_load_access_token_delegates_to_api(settings, httpx_mock) -> None:
    """``load_access_token`` akzeptiert gueltige Tokens (200) und lehnt ungueltige ab (401)."""
    httpx_mock.add_response(url=USERS_ME_URL, method="GET", json={"id": "u1"})
    provider = SchnappsterOAuthProvider(settings)
    access = await provider.load_access_token("good")
    assert access is not None and access.token == "good"

    httpx_mock.add_response(url=USERS_ME_URL, method="GET", status_code=401)
    assert (await provider.load_access_token("bad")) is None


def test_jwt_seconds_until_expiry() -> None:
    """Restlaufzeit wird aus ``exp`` gelesen; ungueltige Tokens ergeben ``None``."""
    assert _jwt_seconds_until_expiry(_fake_jwt(int(time.time()) + 100)) > 0
    assert _jwt_seconds_until_expiry("not-a-jwt") is None
