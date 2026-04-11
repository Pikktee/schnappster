# Schnappster MCP-Server

Remote [Model Context Protocol](https://modelcontextprotocol.io/) Server (**Streamable HTTP**) für die Schnappster-API: Schnäppchen listen, persönliche Einstellungen und Suchaufträge verwalten.

## Voraussetzungen

- Python 3.13+, [`uv`](https://docs.astral.sh/uv/)
- Laufende Schnappster-FastAPI-Instanz
- Supabase-Projekt (wie die Haupt-App)
- **Supabase Access Token** des Nutzers (gleiches JWT wie im Web-Frontend unter `Authorization: Bearer …`)

## Konfiguration (`.env` — wie die Haupt-App)

Es sind **keine** `export`-Zeilen nötig: derselbe **`SUPABASE_URL`** und **`SUPABASE_PUBLISHABLE_KEY`** wie in der Schnappster-**Root-`.env`** werden automatisch geladen (liegt eine Ebene über `mcp-server/`, dieselbe Datei wie für `uv run start`).

Zusätzlich wird optional **`mcp-server/.env`** eingelesen — Werte dort **überschreiben** die Root-`.env`.

Reihenfolge: zuerst Repository-Root `.env`, dann `mcp-server/.env`. Abweichendes Repo-Layout: Umgebungsvariable **`SCHNAPPSTER_ROOT`** (absoluter Pfad zum Schnappster-Repo) setzen.

| Variable | Beschreibung |
| --- | --- |
| `SCHNAPPSTER_API_BASE_URL` | Basis-URL der API (Standard **`http://127.0.0.1:8000`**, für Produktion in `.env` setzen) |
| `SUPABASE_URL` | wie Haupt-App (typisch schon in Root-`.env`) |
| `SUPABASE_PUBLISHABLE_KEY` | wie Haupt-App (typisch schon in Root-`.env`) |
| `MCP_HOST` | Bind-Adresse (Standard `127.0.0.1`) |
| `MCP_PORT` | Port (Standard `8766`) |
| `MCP_RESOURCE_SERVER_URL` | Öffentliche MCP-URL inkl. Pfad, z. B. `https://dein-tunnel.example/mcp`. Wenn nicht gesetzt: `http://MCP_HOST:MCP_PORT/mcp` |
| `STREAMABLE_HTTP_PATH` | MCP-Pfad (Standard `/mcp`) — muss zu `MCP_RESOURCE_SERVER_URL` passen |
| `LOG_LEVEL` | `DEBUG`, `INFO`, … (Standard `INFO`) |

## Start

### CLI-Einstiege (im `mcp-server`-Paket)

| Befehl (meist vom **Repo-Root** mit `uv run …`) | Rolle |
| --- | --- |
| **`mcp-server`** | Komfort-CLI: startet den MCP (wie `schnappster-mcp`) oder mit **`--tunnel`** Quick Tunnel + gesetzter `MCP_RESOURCE_SERVER_URL`. Optional **`--mitmdump`** für mitmproxy und Klartext-Log unter **`logs/`** (Repo-Root). |
| **`schnappster-mcp`** | Nur der Streamable-HTTP-MCP-Server (kein Tunnel). |

Nach `uv sync` im **Schnappster-Root** ist `schnappster-mcp` als **editable** Abhängigkeit installiert — `uv run mcp-server` und `uv run schnappster-mcp` sind verfügbar.

### Vom Repository-Root

```bash
uv run mcp-server
```

**Öffentliche URL in einem Schritt (TryCloudflare + MCP):** Startet `cloudflared` (Quick Tunnel), erkennt die `https://….trycloudflare.com`-URL aus den Logs und startet den MCP mit gesetzter **`MCP_RESOURCE_SERVER_URL`** (inkl. `STREAMABLE_HTTP_PATH`, Standard `/mcp`) — **ohne** `.env` zu ändern. Strg+C beendet Tunnel, ggf. mitmproxy und MCP.

```bash
uv run mcp-server --tunnel
uv run mcp-server --tunnel --port 8766
# Optional: mitmproxy-Trace (Klartext) in Datei unter logs/ (siehe unten):
uv run mcp-server --tunnel --mitmdump
```

**HTTP-Klartext (`--mitmdump`):** Zusätzlich zu **`--tunnel`** (nicht allein). Voraussetzung: **`mitmdump`** im `PATH` (z. B. `brew install mitmproxy`). Es läuft ein **Reverse-Proxy** auf **`--port`** (Standard **8766**) vor `cloudflared`; der MCP bindet auf **`--port + 1`** (Standard **8767**, **`MCP_PORT`**). Die öffentliche MCP-URL bleibt gleich. **mitmdump** schreibt **stdout/stderr** (inkl. Addon `mitm_tunnel_trace_addon.py`: JSON-Bodies, **`Authorization`** maskiert) in eine neue Datei **`logs/mcp_mitmdump_<Zeitstempel>.log`** im **Repository-Root**; auf der Konsole erscheint nur eine Zeile mit dem **absoluten Pfad** (zum `tail -f`). Der Ordner **`logs/`** ist in `.gitignore`. Technisch: MCP-Warmup auf dem Backend-Port, dann mitm + Tunnel, danach MCP-Neustart mit korrekter `MCP_RESOURCE_SERVER_URL`.

Hinweis: Quick Tunnels sind nur für **Entwicklung** gedacht (zufällige Subdomain, kein SLA). **SSE-Limitierung** siehe Abschnitt [Lokales Testen per Tunnel](#lokales-testen-per-tunnel).

Oder nur im Unterprojekt:

```bash
cd mcp-server
uv sync --all-groups
uv run schnappster-mcp
```

Voraussetzung: Root-`.env` enthält mindestens die Supabase-Keys (wie für die FastAPI). Läuft die API auf einem anderen Host/Port, `SCHNAPPSTER_API_BASE_URL` in Root- oder `mcp-server/.env` setzen.

- MCP-Endpunkt: `http://MCP_HOST:MCP_PORT` + `STREAMABLE_HTTP_PATH` (Standard **`http://127.0.0.1:8766/mcp`**)
- Healthcheck (ohne Auth): **`GET /health`**

## Clients (Cursor, Claude Desktop, ChatGPT)

1. **HTTPS-URL** des MCP-Endpunkts eintragen (lokal ggf. Tunnel, siehe unten).
2. **OAuth (empfohlen mit Cursor):** Supabase **OAuth 2.1 Server** + Consent-UI auf der Schnappster-Web-App — Schritt-für-Schritt in [`docs/mcp-server-implementation.md`](../docs/mcp-server-implementation.md) (Abschnitt *Vollständiger Remote-MCP-OAuth-Flow*).
3. **Fallback:** `Bearer <Supabase Access Token>` — sofern der Client Custom-Header unterstützt.

Exakte JSON-Configs ändern sich je nach Produktversion; bitte die jeweilige MCP-Doku öffnen und URL + Header setzen.

## Lokales Testen per Tunnel

### Was ist das?

Dein MCP-Server läuft nur auf **`127.0.0.1`** — aus dem Internet (und manchmal auch aus anderen Tools) ist das nicht erreichbar. Ein **Tunnel** ist ein kleines **Zusatzprogramm** auf deinem Rechner: Es baut eine **verschlüsselte Verbindung** zu einem Anbieter (Cloudflare, ngrok, …) auf und bekommt eine **öffentliche `https://…`-Adresse**, die auf deinen lokalen Port **8766** weiterleitet. Du installierst den Tunnel **einmal**; Schnappster liefert ihn **nicht** mit.

### Tunnel-Software installieren (eine Variante reicht)

#### A) Cloudflare (`cloudflared`) / TryCloudflare

- Laut [Cloudflare-Doku zu Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/): **kein Cloudflare-Account**, nur `cloudflared` installieren und `cloudflared tunnel --url …` ausführen — es entsteht eine zufällige **`https://….trycloudflare.com`-URL**.
- **Limit (SSE):** Quick Tunnels unterstützen **kein Server-Sent Events (SSE)** ([Limitations](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)). Unser MCP nutzt **Streamable HTTP** mit **`json_response=True`**: der **Kern-RPC läuft über POST mit JSON** — das ist **nicht** vom gleichen SSE-Pfad betroffen wie ein reiner Event-Stream. **Wenn** dein Client für diesen Endpunkt **SSE über GET** zwingend braucht, ist TryCloudflare **erwartbar ungeeignet**; dann **ngrok** (Variante B) oder einen anderen Tunnel nutzen.
- **Bequem aus dem Repo-Root:** `uv run mcp-server --tunnel` startet Quick Tunnel **und** MCP mit gesetzter `MCP_RESOURCE_SERVER_URL`. Optional **`--mitmdump`** für **mitmproxy** und Logdatei unter **`logs/`** (siehe [Start](#start)). **Nur** den Tunnel (MCP separat): z. B. `cloudflared tunnel --url http://127.0.0.1:8766`. Auf **macOS** wird fehlendes `cloudflared` bei `--tunnel` einmalig per **`brew install cloudflared`** versucht (Homebrew muss installiert sein).
- Manuelle Installation: [cloudflared herunterladen](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)

#### B) ngrok

- Konto unter [ngrok.com](https://ngrok.com) anlegen, **Authtoken** aus dem Dashboard kopieren.
- Install: [ngrok Download](https://ngrok.com/download) oder `brew install ngrok`
- Einmalig: `ngrok config add-authtoken <DEIN_TOKEN>`

### Ablauf (nach Installation)

1. **Schnappster-API** laufen lassen (`uv run start` o. ä.), damit der MCP proxyen kann.
2. **MCP + Quick Tunnel in einem Terminal** (empfohlen für TryCloudflare):

   ```bash
   uv run mcp-server --tunnel
   ```

   In der Ausgabe erscheint die gesetzte **`MCP_RESOURCE_SERVER_URL`** (inkl. `/mcp`). Im **MCP-Client** dieselbe URL eintragen und **`Authorization: Bearer <Supabase Access Token>`** setzen.

   **Alternativen:** MCP und Tunnel getrennt (z. B. zwei Terminals): `cloudflared tunnel --url http://127.0.0.1:8766` und **`uv run mcp-server`** (oder `uv run schnappster-mcp`). Dann **`MCP_RESOURCE_SERVER_URL`** in Root- oder `mcp-server/.env` setzen (z. B. `https://abc.trycloudflare.com/mcp`) und **MCP neu starten**.

3. **Variante B (ngrok)** — wenn du kein Quick Tunnel willst oder SSE-Probleme hast:

   ```bash
   uv run mcp-server
   ngrok http 8766
   ```

   Öffentliche **HTTPS-URL** aus der ngrok-Ausgabe notieren, **`/mcp` anhängen**, in `.env` als `MCP_RESOURCE_SERVER_URL` setzen und MCP neu starten (wie oben).

**Sicherheit:** Solange der Tunnel läuft, ist dein lokaler MCP aus dem Netz erreichbar — Tunnel bei Nichtgebrauch **beenden**; keine Secrets in Repos committen.

## Tools

| Tool | Zweck |
| --- | --- |
| `list_recent_bargains` | Analysierte Ads, sortiert nach Score |
| `get_my_settings` / `update_my_settings` | Persönliche Nutzereinstellungen |
| `list_ad_searches` / `get_ad_search` / `create_ad_search` / `update_ad_search` / `delete_ad_search` | Suchaufträge |

## Tests

```bash
cd mcp-server
uv run pytest
```
