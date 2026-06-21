"""OAuth-2.1-Authorization-Server fuer den Remote-MCP-Server.

Der mcp-server ist selbst der Authorization-Server (Variante A): Dynamic Client
Registration, eine kleine Login-Seite (prueft E-Mail/Passwort gegen die Schnappster-API
``POST /auth/login``) und Token-Ausgabe nach dem Authorization-Code-Flow mit PKCE.

Das ausgegebene Access-Token IST das App-JWT der Schnappster-API; validiert wird es
zustandslos ueber ``GET /users/me/`` (siehe :class:`ApiTokenVerifier`). Dadurch ueberleben
laufende Sitzungen Redeploys, und es muss kein Signatur-Secret mit der API geteilt werden.

Refresh-Tokens werden bewusst nicht ausgegeben: Ein neues App-JWT laesst sich ohne Passwort
nicht praegen. Laeuft das Token ab (7 Tage), verbindet der Client per Login-Seite neu.
"""

import base64
import binascii
import json
import secrets
import time

import httpx
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from schnappster_mcp.core.auth import ApiTokenVerifier
from schnappster_mcp.core.config import Settings

# Kurzlebige Handshake-Artefakte: Login-Transaktion und Authorization-Code.
_PENDING_TTL_S = 600  # 10 Minuten fuer den Login-Vorgang auf der Seite
_AUTH_CODE_TTL_S = 60  # Code wird sofort gegen Token getauscht


class LoginError(Exception):
    """Fuer den Endnutzer anzeigbarer Fehler waehrend des Logins auf der OAuth-Seite."""


class SchnappsterAuthorizationCode(AuthorizationCode):
    """Authorization-Code mit dem bereits gepraegten App-JWT (Subject-Token)."""

    app_jwt: str


class _PendingAuthorization:
    """Zwischengespeicherte ``/authorize``-Parameter bis der Nutzer sich eingeloggt hat."""

    def __init__(self, client_id: str, params: AuthorizationParams) -> None:
        """Bindet die Authorization-Parameter an den anfragenden Client samt Zeitstempel."""
        self.client_id = client_id
        self.params = params
        self.created_at = time.time()


class SchnappsterOAuthProvider(
    OAuthAuthorizationServerProvider[
        SchnappsterAuthorizationCode, RefreshToken, AccessToken
    ]
):
    """OAuth-Provider: DCR, Login gegen die API, Code->Token-Tausch, Token-Validierung."""

    def __init__(self, settings: Settings) -> None:
        """Initialisiert In-Memory-Stores und den API-basierten Token-Verifier."""
        self._settings = settings
        self._verifier = ApiTokenVerifier(settings)
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._pending: dict[str, _PendingAuthorization] = {}
        self._auth_codes: dict[str, SchnappsterAuthorizationCode] = {}

    # --- Dynamic Client Registration -------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        """Liefert die registrierten Client-Daten oder ``None``."""
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Speichert einen dynamisch registrierten Client (DCR)."""
        self._clients[client_info.client_id] = client_info

    # --- Authorization-Endpoint: auf Login-Seite umleiten ----------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Merkt sich die Anfrage und leitet den Browser auf die Login-Seite um."""
        self._prune()
        txn = secrets.token_urlsafe(32)
        self._pending[txn] = _PendingAuthorization(client.client_id, params)
        return f"{self._settings.mcp_issuer_url}/oauth/login?txn={txn}"

    async def complete_login(self, txn: str, email: str, password: str) -> str:
        """Prueft Credentials, legt einen Authorization-Code an und liefert die Redirect-URL.

        Wird von der Login-POST-Route aufgerufen (nicht Teil des Provider-Protokolls).
        ``LoginError`` signalisiert eine fuer den Nutzer anzeigbare Fehlermeldung.
        """
        self._prune()
        pending = self._pending.get(txn)
        if pending is None:
            raise LoginError("Sitzung abgelaufen. Bitte erneut verbinden.")

        app_jwt = await self._login_against_api(email, password)

        code = secrets.token_urlsafe(32)
        params = pending.params
        self._auth_codes[code] = SchnappsterAuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + _AUTH_CODE_TTL_S,
            client_id=pending.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
            app_jwt=app_jwt,
        )
        del self._pending[txn]
        return construct_redirect_uri(
            str(params.redirect_uri), code=code, state=params.state
        )

    # --- Token-Endpoint --------------------------------------------------------------

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> SchnappsterAuthorizationCode | None:
        """Laedt einen gueltigen, nicht abgelaufenen Code dieses Clients (sonst ``None``)."""
        code = self._auth_codes.get(authorization_code)
        if code is None or code.client_id != client.client_id:
            return None
        if code.expires_at < time.time():
            self._auth_codes.pop(authorization_code, None)
            return None
        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: SchnappsterAuthorizationCode,
    ) -> OAuthToken:
        """Tauscht den (einmalig nutzbaren) Code gegen das App-JWT als Access-Token."""
        code = self._auth_codes.pop(authorization_code.code, None)
        if code is None:
            raise TokenError("invalid_grant", "Authorization code already used or expired")
        return OAuthToken(
            access_token=code.app_jwt,
            token_type="Bearer",
            expires_in=_jwt_seconds_until_expiry(code.app_jwt),
            scope=" ".join(code.scopes) if code.scopes else None,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        """Es werden keine Refresh-Tokens ausgegeben."""
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        """Nicht unterstuetzt — neu einloggen, sobald das Access-Token abgelaufen ist."""
        raise TokenError("invalid_grant", "Refresh tokens are not supported")

    # --- Token-Validierung (Resource-Server) -----------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Validiert das Bearer-Token zustandslos ueber ``GET /users/me/`` der API."""
        return await self._verifier.verify_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        """Kein serverseitiger Token-Store; Access-Tokens laufen ueber ihre JWT-Lebensdauer ab."""

    # --- Intern ----------------------------------------------------------------------

    async def _login_against_api(self, email: str, password: str) -> str:
        """Loggt sich gegen ``POST /auth/login`` ein und liefert das App-JWT."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self._settings.login_url,
                    json={"email": email, "password": password},
                )
        except httpx.HTTPError as exc:
            raise LoginError("Login-Server ist nicht erreichbar.") from exc

        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return str(token)
            raise LoginError("Unerwartete Antwort vom Login-Server.")
        if response.status_code == 403:
            raise LoginError("Konto ist noch nicht freigeschaltet.")
        raise LoginError("E-Mail oder Passwort ist falsch.")

    def _prune(self) -> None:
        """Entfernt abgelaufene Login-Transaktionen und Authorization-Codes."""
        now = time.time()
        self._pending = {
            k: v for k, v in self._pending.items() if now - v.created_at < _PENDING_TTL_S
        }
        self._auth_codes = {
            k: v for k, v in self._auth_codes.items() if v.expires_at >= now
        }


def _jwt_seconds_until_expiry(token: str) -> int | None:
    """Liest ``exp`` aus dem JWT (ohne Signaturpruefung) und gibt die Restlaufzeit zurueck."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        exp = json.loads(decoded).get("exp")
    except (binascii.Error, ValueError, TypeError):
        return None
    if not isinstance(exp, int | float):
        return None
    return max(0, int(exp - time.time()))
