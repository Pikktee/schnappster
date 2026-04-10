# Schnappster - Architektur

## Uebersicht

Die folgenden Diagramme visualisieren die Architektur der Anwendung.

### 1. Systemueberblick

#### Produktion (Zielbild: Vercel + Railway)

Web und API laufen als getrennte Deployments mit eigenen Domains:

- **Frontend (Vercel):** `https://app.<domain>`
- **Backend API (Railway):** `https://api.<domain>`
- **Routing:** Frontend ruft API unter `https://api.<domain>/api/...` auf
- **TLS/HTTPS:** wird durch Vercel und Railway + DNS-Domain-Mapping bereitgestellt

Das Backend beinhaltet weiterhin den kompletten fachlichen Runtime-Anteil:

- **FastAPI** mit Endpunkten unter `/api`
- **APScheduler** fuer Scrape-, Analyze- und Cleanup-Jobs (im API-Prozess)
- **ScraperService** -> **Kleinanzeigen.de**
- **AIService** -> **OpenAI-kompatible API**
- **Benachrichtigungen** -> **Telegram-Bot**
- **Persistenz** -> Datenbank gemaess aktueller Konfiguration/Umgebung

CORS ist in der Produktion notwendig, da Frontend und API auf unterschiedlichen Origins laufen.

#### Development

Lokal bleiben Frontend und API ebenfalls getrennt:

- **Next.js Dev Server:** `http://localhost:3000`
- **FastAPI API:** `http://localhost:8000/api/...`
- **CORS:** `localhost:3000` muss fuer die lokale API freigegeben sein

Die Background Jobs laufen lokal wie in Produktion im FastAPI-Prozess.

### 2. Backend-Schichten (`architecture-backend-layers.png`)

Zeigt die Schichten des Backends (von aussen nach innen). **Pfeil** = "nutzt".
Quelle: `architecture-backend-layers.mmd` (Mermaid).
PNG neu erzeugen:
`npx -p @mermaid-js/mermaid-cli mmdc -i architecture-backend-layers.mmd -o architecture-backend-layers.png`

- **Entry:** `main.py` -> `create_app()` in `core/bootstrap.py` (CORS, Lifespan, Router)
- **routes/api:** REST-Endpunkte (ads, adsearch, aianalysislogs, errorlogs, scraperuns, settings, version)
- **services:** ScraperService, AIService, SettingsService, Telegram
- **scraper:** HTTP/HTML (httpclient, parser) - keine Business-Logik
- **models:** SQLModel-Tabellen und API-Schemas
- **core:** DB, Config, Logging, BackgroundJobs (APScheduler)
- **cli:** Einstiegspunkte (`uv run start`, `scrape`, `analyze`, `dbreset`); nutzt services, core, models

Hinweis: Der fruehere Frontend-Mount im FastAPI-Bootstrap ist nicht mehr Teil des Zielbilds fuer Produktion.

### 3. Scheduler- und Analyze-Flow (`architecture-scheduler-flow.png`)

Zeigt, wann Scrape- und Analyze-Jobs laufen und wie der Analyze-Backlog abgearbeitet wird.
Quelle: `architecture-scheduler-flow.mmd`.
PNG neu erzeugen:
`npx -p @mermaid-js/mermaid-cli mmdc -i architecture-scheduler-flow.mmd -o architecture-scheduler-flow.png`

- **Beim Start:** `initial_scrape`, `initial_analyze` und `initial_cleanup` laufen einmal.
- **Alle 1 Min:** Scrape prueft faellige Suchen; bei neuen Ads wird ein Analyze-Job in die Analyzer-Queue gestellt.
- **Analyze-Lauf:** Verarbeitet bis zu 10 unanalysierte Ads; bei verbleibendem Backlog wird erneut gequeued.
- **Cleanup:** Alle 24 h und einmal beim Start - loescht alte Anzeigen gemaess `auto_delete_ads_days`.

### 4. Geplanter MCP-Service auf Railway

Fuer den kommenden MCP-Server ist die empfohlene Betriebsform ein eigener Railway-Service:

- Separater Deploy neben der API (kein gemeinsamer Prozess)
- Eigene Umgebungsvariablen und Secrets
- Eigene Logs, Healthchecks und Rollback-Historie
- Optional eigene Domain (z. B. `mcp.<domain>`) oder interner Service-Zugriff

Damit bleiben API und MCP operativ entkoppelt, auch bei separaten Releases.
