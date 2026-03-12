# Schnappster – Architektur

## Übersicht

Die folgenden Diagramme visualisieren die Architektur der Anwendung.

### 1. Systemüberblick

#### Produktion (`architecture-overview.png`)

**Ein Server auf :8000** – `uv run start` (ohne `--dev`): FastAPI liefert API und statisches Frontend aus einem Prozess.

- **User/Browser** → **FastAPI App (:8000)** (API unter `/api`, statisches Frontend aus `web/out`: Next.js 16, React 19, Tailwind v4, shadcn/ui)
- FastAPI nutzt **SQLite** (`data/schnappster.db`)
- **APScheduler** (Background Jobs): Scrape-Job alle 1 Min (und einmal beim Start). Analyze-Job einmal beim Start (Backlog abarbeiten) und nach jedem Scrape bei neuen Anzeigen; jeder Analyze-Lauf verarbeitet bis zu 10 Ads und queued bei verbleibendem Backlog den nächsten Lauf (Re-Queue bis leer). Cleanup-Job alle 24 h und einmal beim Start (löscht Anzeigen älter als konfigurierte Tage).
- **ScraperService** → **Kleinanzeigen.de**, **AIService** → **OpenAI-kompatible API**
- **Benachrichtigungen** → **Telegram-Bot**

#### Development (`architecture-overview-dev.png`)

**Zwei getrennte Prozesse** – `uv run start --dev`: Frontend und API laufen auf verschiedenen Ports, CORS aktiv.

- **Benutzer/Browser** ↔ **Next.js Dev Server (:3000)** (React 19, Tailwind, shadcn/ui, Hot Reload) für die App; **API-Anfragen (CORS)** gehen vom Browser direkt an **FastAPI API (:8000)** (nur `/api`).
- Zwischen :3000 und :8000: **CORS** (Cross-Origin-Requests); das Frontend ruft die API unter :8000 auf.
- **APScheduler** (Scrape Job, Analyze Job, Cleanup Job) läuft **intern** im FastAPI-Prozess (`core/background_jobs.py`), kein separater Dienst. Beim Start: einmal Scrape, einmal Analyze, einmal Cleanup; Analyze wird bei neuem Scrape-Output und bei verbleibendem Backlog (Re-Queue) erneut gequeued. Cleanup alle 24 h (Anzeigen älter als konfigurierte Tage löschen).
- DB, ScraperService, AIService und Telegram hängen am FastAPI-Prozess (:8000); die **SQLite-DB** wird von FastAPI gelesen und geschrieben (bidirektional).

### 2. Backend-Schichten (`architecture-backend-layers.png`)

Zeigt die Schichten des Backends (von außen nach innen). **Pfeil** = „nutzt“. Quelle: `architecture-backend-layers.mmd` (Mermaid). PNG neu erzeugen: `npx -p @mermaid-js/mermaid-cli mmdc -i architecture-backend-layers.mmd -o architecture-backend-layers.png`

- **Entry:** `main.py` → `create_app()` in `core/bootstrap.py` (CORS, Lifespan, Router, Static Mount)
- **routes/api:** REST-Endpunkte (ads, adsearch, aianalysislogs, errorlogs, scraperuns, settings, version)
- **routes/frontend:** SPA-Fallback für `/searches/{id}` und `/ads/{id}`, Mount von `web/out`
- **services:** ScraperService, AIService, SettingsService, Telegram
- **scraper:** HTTP/HTML (httpclient, parser) – keine Business-Logik
- **models:** SQLModel-Tabellen und API-Schemas
- **core:** DB, Config, Logging, BackgroundJobs (APScheduler)
- **cli:** Einstiegspunkte (`uv run start`, `scrape`, `analyze`, `dbreset`); nutzt services, core, models (gestrichelte Pfeile)

### 3. Scheduler- und Analyze-Flow (`architecture-scheduler-flow.png`)

Zeigt, wann Scrape- und Analyze-Jobs laufen und wie der Analyze-Backlog abgearbeitet wird. Quelle: `architecture-scheduler-flow.mmd`. PNG neu erzeugen: `npx -p @mermaid-js/mermaid-cli mmdc -i architecture-scheduler-flow.mmd -o architecture-scheduler-flow.png`

- **Beim Start:** `initial_scrape`, `initial_analyze` und `initial_cleanup` laufen einmal.
- **Alle 1 Min:** Scrape prüft fällige Suchen; bei neuen Ads wird ein Analyze-Job in die Analyzer-Queue gestellt.
- **Analyze-Lauf:** Verarbeitet bis zu 10 unanalysierte Ads; wenn danach noch Backlog besteht und mindestens eine Ad analysiert wurde, wird der nächste Analyze-Job gequeued (Re-Queue bis Backlog leer).
- **Cleanup:** Alle 24 h und einmal beim Start – löscht Anzeigen älter als die in den Einstellungen konfigurierte Anzahl Tage (`auto_delete_ads_days`).
