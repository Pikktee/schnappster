# Schnappster Remote-MCP — Implementierung und Betrieb (Kernpunkte)

Dieses Dokument fasst die wichtigsten Entscheidungen und Konzepte rund um den **Schnappster MCP-Server** (`mcp-server/`), Tunnel, CLI, Auth und Cursor zusammen — ergänzend zu [`mcp-server/README.md`](../mcp-server/README.md).

## Architektur kurz

- **MCP-Paket:** [`mcp-server/schnappster_mcp/`](../mcp-server/schnappster_mcp/) — Streamable HTTP, FastMCP, Tools rufen die Schnappster-API mit Bearer-Token auf.
- **Zwei CLI-Einstiege** (im Unterprojekt [`mcp-server/pyproject.toml`](../mcp-server/pyproject.toml)):
  - **`schnappster-mcp`** — nur der HTTP-Server.
  - **`mcp-server`** — startet denselben Server oder **Quick Tunnel + Server** (`--tunnel`), setzt dabei `MCP_RESOURCE_SERVER_URL` für den Kindprozess (ohne `.env` zu ändern).
- **Root-Projekt:** `schnappster-mcp` ist als **editable** Abhängigkeit eingetragen; `uv run mcp-server` / `uv run schnappster-mcp` funktionieren vom Repo-Root nach `uv sync`.

## Tunnel: nur Quick Tunnel (TryCloudflare)

- **Gewählt:** Cloudflare **Quick Tunnel** (`*.trycloudflare.com`) — kein Cloudflare-Account nötig für den Quick-Flow, keine Nameserver-Umstellung, keine Tunnel-API.
- **Benannter / „richtiger“ Cloudflare-Tunnel** (eigene Domain, DNS, Connector) ist im Projekt **nicht** dokumentiert (höherer Betriebsaufwand); bei Bedarf [Cloudflare Tunnel Guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/) konsultieren.
- **Limit:** Quick Tunnels unterstützen **kein SSE**; siehe [TryCloudflare Limitations](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/). Der Schnappster-MCP nutzt **`json_response=True`** — der Kern-RPC über **POST + JSON** ist davon unabhängig; Clients, die **zwingend SSE über GET** brauchen, sind mit TryCloudflare schlecht beraten (Alternativen: z. B. ngrok, siehe README).

## stdio vs. Remote MCP

- **stdio:** Konfiguration mit **`command`** + **`args`** (z. B. `npx @railway/mcp-server`) — lokaler Prozess, MCP über stdin/stdout.
- **Remote (Schnappster):** **HTTPS-URL** zum Endpunkt (inkl. Pfad, typisch `/mcp`), kein `npx`-Wrapper in Cursor nötig.

## Authentifizierung

### Issuer und Token

- **`issuer_url`** in FastMCP zeigt auf **Supabase Auth** (`…/auth/v1`), nicht auf eine separate „Schnappster-OAuth“-Instanz.
- **Verifier:** [`SupabaseTokenVerifier`](../mcp-server/schnappster_mcp/auth.py) — prüft Tokens per `GET …/auth/v1/user` (gleiche Idee wie im Web-Frontend).
- **Öffentliche MCP-URL:** `MCP_RESOURCE_SERVER_URL` muss zur erreichbaren HTTPS-URL passen (OAuth-/Protected-Resource-Metadaten).

### OAuth in Cursor vs. manuelles Bearer

- **Cursor** kann bei **Remote-MCP** einen **OAuth-Browser-Flow** anbieten — dann ist kein manuelles Kopieren des Tokens nötig, sofern alles konfiguriert ist.
- **Fallback:** README beschreibt weiterhin **Bearer** (Supabase Access Token), wenn der Client keinen OAuth macht oder der Flow scheitert.

### Redirect-URL in Supabase (Cursor)

- Cursor nutzt für MCP-OAuth eine **feste Redirect-URL**, siehe [Cursor MCP Docs](https://cursor.com/docs/mcp#installing-mcp-servers):
  - `cursor://anysphere.cursor-mcp/oauth/callback`
- Diese URL muss in **Supabase → Authentication → URL Configuration / Redirect URLs** erlaubt sein (Custom Scheme `cursor://` ist bei Supabase grundsätzlich möglich; ggf. Wildcards laut [Supabase Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)).
- **Andere Clients** (Claude, ChatGPT, …): **eigene** Redirect-URIs je nach Hersteller-Doku — alle, die ihr unterstützen wollt, in Supabase eintragen.

### Branding / „Login-Seite“

- **Verbindungsfreigabe (Endnutzer):** Route **`/connect`** — dort landen Nutzer, nachdem Supabase zur eigenen UI weiterleitet (nur wenn **OAuth 2.1 Server** aktiv ist und der **Authorization Path** in Supabase exakt **`/connect`** ist). Technisch nutzt die Seite `supabase.auth.oauth.*` (siehe [Supabase Getting Started](https://supabase.com/docs/guides/auth/oauth-server/getting-started)). Ohne OAuth-Server bleibt die Seite wirkungslos. Kurzinfo für Nutzer bleibt auf **`/mcp-connect`** (Hilfe/Kopier-URL), nicht mit **`/connect`** verwechseln.
- **Optional:** Hilfsseite **`/mcp-connect`** (Kurzanleitung Cursor). Öffentliche MCP-URL optional per **`NEXT_PUBLIC_MCP_ENDPOINT_URL`** (Kopier-Button).
- Nach **Cursor-initiiertem** OAuth endet der Browser-Teil typischerweise bei **Cursor** („Tab schließen“) — nicht zwingend auf eurer Domain.

### Vollständiger Remote-MCP-OAuth-Flow (Supabase OAuth 2.1 Server + Cursor)

Ziel: Cursor startet den OAuth-Code-Flow gegen **Supabase**; Nutzer melden sich bei Schnappster an und bestätigen die Freigabe auf **`/connect`**; anschließend erhält Cursor Tokens über Supabase.

Offizielle Übersicht (Discovery, optional Dynamic Registration, Troubleshooting): [Model Context Protocol (MCP) Authentication](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication), insbesondere [OAuth client setup](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication#oauth-client-setup).

MCP-Clients ermitteln die OAuth-Server-Metadaten u. a. über  
`https://<project-ref>.supabase.co/.well-known/oauth-authorization-server/auth/v1` — das passt zum **Issuer** `https://<project-ref>.supabase.co/auth/v1`, den der Schnappster-MCP aus **`SUPABASE_URL`** ableitet (keine separate Eintragung dieser URLs in der Schnappster-`.env` nötig).

#### 1. Supabase: OAuth 2.1 Server aktivieren

1. Dashboard → **Authentication** → **OAuth Server**.
2. **OAuth 2.1 server capabilities** einschalten (Feature derzeit in **Beta**, siehe [OAuth 2.1 Server](https://supabase.com/docs/guides/auth/oauth-server)).
3. **Authorization Path** setzen — muss exakt zur Schnappster-Route passen: **`/connect`** (ohne Domain; Supabase setzt ihn mit der **Site URL** zusammen).

#### 2. Supabase: Site URL und Redirects

1. **Authentication** → **URL Configuration** → **Site URL** = öffentliche Basis-URL der Next.js-App, unter der **`/connect`** erreichbar ist (lokal z. B. `http://localhost:3000`, Produktion z. B. `https://app.example.com`). **Muss** mit der URL übereinstimmen, die Nutzer im Browser sehen, sonst stimmt die Weiterleitung nach der Autorisierung nicht.
2. **Redirect URLs:** mindestens  
   - `cursor://anysphere.cursor-mcp/oauth/callback` (Cursor MCP),  
   - dieselbe **Site URL** und ggf. `http://localhost:3000/**` / Vorschau-Domains,  
   - OAuth-Provider-Callbacks wie von Supabase vorgegeben (Google/Facebook usw.).

#### 3. OAuth-Client für MCP (laut Supabase zwei Optionen)

Siehe [OAuth client setup](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication#oauth-client-setup):

| Variante | Wann | Dashboard / Aktion |
| --- | --- | --- |
| **Manuell** | Volle Kontrolle, kein dynamisches Registrieren | OAuth-Client anlegen, [Register an OAuth client](https://supabase.com/docs/guides/auth/oauth-server/getting-started#register-an-oauth-client); Credentials ggf. im MCP-Client nutzen, sofern unterstützt. |
| **Dynamisch** | Bequem für Tools wie Cursor ohne vorherige Client-Anlage | **Authentication → OAuth Server:** **Allow Dynamic OAuth Apps** (oder gleichlautender Schalter) aktivieren. |

Dynamic Registration bedeutet nicht ohne Redirect-Regeln: Supabase weist u. a. darauf hin, **Redirect-URIs** der Clients zu prüfen („valid, complete URLs“) und [Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls) / Nutzer-Freigabe (`/connect`) ernst zu nehmen.

#### 4. Schnappster lokal starten

1. **API:** `uv run start --skip-tests` (oder `--dev`), damit `SCHNAPPSTER_API_BASE_URL` erreichbar ist.
2. **Frontend:** `cd web && npm run dev` (oder über `uv run start --dev`), damit die Freigabeseite unter der Site URL erreichbar ist (lokal z. B. **`http://localhost:3000/connect/`** mit Next.js `trailingSlash`).
3. **MCP:** `uv run mcp-server --tunnel`, öffentliche **`MCP_RESOURCE_SERVER_URL`** aus der Konsole notieren.

#### 5. Cursor

Remote-MCP mit der Tunnel-**HTTPS**-URL inkl. **`/mcp`** eintragen und **OAuth** / Anmeldung wählen (kein manuelles Bearer nötig). Beim ersten Connect sollte der Browser Supabase → ggf. Login → **`/connect`** → danach Rückleitung zu Cursor öffnen.

#### 6. Typische Fehler

| Symptom | Prüfen |
| --- | --- |
| Nach Authorize 404 auf eurer Domain | Site URL + Authorization Path = vollständige URL der Freigabeseite (`…/connect`) |
| `authorization_id` fehlt | Authorization Path in Supabase muss **`/connect`** sein; Route `web/app/connect/` |
| Discovery / Registration schlägt fehl | OAuth 2.1 Server wirklich aktiv; ggf. Dynamic Registration; Projekt-URL erreichbar |
| Cursor-Callback abgelehnt | `cursor://anysphere.cursor-mcp/oauth/callback` in Redirect URLs |
| Cursor: **Invalid Host header** nach OAuth (Streamable HTTP) | FastMCP DNS-Rebinding: öffentlicher Host muss zu **`MCP_RESOURCE_SERVER_URL`** passen (Tunnel-URL setzt die CLI); in aktuellen Schnappster-Versionen wird der Host daraus automatisch erlaubt. |

## Tests und Konfiguration (Kurz)

1. Root: **`uv sync`**, `.env` mit Supabase + `SCHNAPPSTER_API_BASE_URL`.
2. API laufen lassen (`uv run start` o. ä.).
3. **`uv run mcp-server`** lokal oder **`uv run mcp-server --tunnel`** für öffentliche TryCloudflare-URL + gesetztes `MCP_RESOURCE_SERVER_URL`.
4. **`GET /health`** am MCP-Port ohne Auth.
5. Cursor: Remote-MCP-URL eintragen; OAuth oder Bearer laut README.

## Verweise

| Thema | Ort |
| -------- | ----- |
| Befehle, Env, Tunnel, Clients | [`mcp-server/README.md`](../mcp-server/README.md) |
| Root-Befehle inkl. `mcp-server` | [`AGENTS.md`](../AGENTS.md) |
| MCP-Connect-Webseite | `web/app/mcp-connect/` |
| Verbindungsfreigabe (Supabase OAuth Server) | `web/app/connect/` |
| MCP-Server-Build / Auth-Code | [`mcp-server/schnappster_mcp/server.py`](../mcp-server/schnappster_mcp/server.py) |
| Supabase: MCP + OAuth-Client-Setup | [MCP Authentication → OAuth client setup](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication#oauth-client-setup) |
