# Schnappster – Architektur

## Übersicht

Die folgenden Diagramme visualisieren die Architektur der Anwendung.

### 1. Systemüberblick

#### Produktion (`architecture-overview.png`)

**Ein Server auf :8000** – `uv run start` (ohne `--dev`): FastAPI liefert API und statisches Frontend aus einem Prozess.

- **User/Browser** → **FastAPI App (:8000)** (API unter `/api`, statisches Frontend aus `web/out`: Next.js 16, React 19, Tailwind v4, shadcn/ui)
- FastAPI nutzt **SQLite** (`data/schnappster.db`)
- **APScheduler** (Background Jobs): Scrape-Job alle 1 Min (und einmal beim Start); bei neuen Anzeigen → Analyze-Job
- **ScraperService** → **Kleinanzeigen.de**, **AIService** → **OpenAI-kompatible API**
- **Benachrichtigungen** → **Telegram-Bot**

#### Development (`architecture-overview-dev.png`)

**Zwei getrennte Prozesse** – `uv run start --dev`: Frontend und API laufen auf verschiedenen Ports, CORS aktiv.

- **Benutzer/Browser** ↔ **Next.js Dev Server (:3000)** (React 19, Tailwind, shadcn/ui, Hot Reload) für die App; **API-Anfragen (CORS)** gehen vom Browser direkt an **FastAPI API (:8000)** (nur `/api`).
- Zwischen :3000 und :8000: **CORS** (Cross-Origin-Requests); das Frontend ruft die API unter :8000 auf.
- **APScheduler** (Scrape Job, Analyze Job) läuft **intern** im FastAPI-Prozess (`core/background_jobs.py`), kein separater Dienst.
- DB, ScraperService, AIService und Telegram hängen am FastAPI-Prozess (:8000); die **SQLite-DB** wird von FastAPI gelesen und geschrieben (bidirektional).

### 2. Backend-Schichten (`architecture-backend-layers.png`)

Zeigt die Schichten des Backends (von außen nach innen). **Pfeil** = „nutzt“. Quelle: `architecture-backend-layers.mmd` (Mermaid). PNG neu erzeugen: `npx -p @mermaid-js/mermaid-cli mmdc -i architecture-backend-layers.mmd -o architecture-backend-layers.png`

- **Entry:** `main.py` → `create_app()` in `core/bootstrap.py` (CORS, Lifespan, Router, Static Mount)
- **routes/api:** REST-Endpunkte (ads, adsearch, errorlogs, scraperuns, settings)
- **routes/frontend:** SPA-Fallback für `/searches/{id}` und `/ads/{id}`, Mount von `web/out`
- **services:** ScraperService, AIService, SettingsService, Telegram
- **scraper:** HTTP/HTML (httpclient, parser) – keine Business-Logik
- **models:** SQLModel-Tabellen und API-Schemas
- **core:** DB, Config, Logging, BackgroundJobs (APScheduler)
- **cli:** Einstiegspunkte (`uv run start`, `scrape`, `analyze`, `dbreset`); nutzt services, core, models (gestrichelte Pfeile)
