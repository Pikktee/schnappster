# Schnappster – Projekt-Kontext

## Was ist Schnappster?
Eine persönliche Web-App die Kleinanzeigen.de-Suchergebnisse periodisch scrapt, mit KI auf Schnäppchen analysiert und die Ergebnisse in einem Dashboard anzeigt.

## Tech Stack
- **Backend:** Python 3.13, FastAPI, SQLModel, SQLite, curl-cffi (Scraping), OpenRouter API (KI-Analyse)
- **Frontend:** Vue 3 + shadcn-vue (noch nicht gebaut)
- **Tools:** uv (Package Manager), Ruff (Linting), Pyright (Type Checking), Rich (Logging), Cursor IDE

## Projektstruktur

```
schnappster/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI App mit Lifespan (init_db, scheduler)
│   ├── api/
│   │   ├── __init__.py          # api_router bündelt alle Router
│   │   ├── ads.py               # GET /api/ads/, GET /api/ads/{id}
│   │   ├── adsearch.py          # CRUD /api/adsearches/ (GET, POST, PATCH, DELETE)
│   │   ├── errorlogs.py         # GET /api/errorlogs/
│   │   ├── scraperuns.py        # GET /api/scraperuns/
│   │   └── settings.py          # GET/PUT /api/settings/
│   ├── core/
│   │   ├── __init__.py          # Re-exportiert: DbSession, engine, init_db, settings, setup_logging, get_app_root, start/stop_scheduler
│   │   ├── db.py                # SQLModel Engine, DbSession (Annotated), init_db()
│   │   ├── logging.py           # setup_logging() mit RichHandler
│   │   ├── scheduler.py         # APScheduler: check_and_scrape (1min), analyze_ads (2min)
│   │   └── settings.py          # Pydantic Settings (.env), get_app_root()
│   ├── models/
│   │   ├── __init__.py          # Re-exportiert alle Models
│   │   ├── ad.py                # Ad (Table) + AdRead (Schema)
│   │   ├── adsearch.py          # AdSearch (Table) + AdSearchCreate/Read/Update (Schemas)
│   │   ├── errorlog.py          # ErrorLog (Table) + ErrorLogRead
│   │   ├── scraperun.py         # ScrapeRun (Table) + ScrapeRunRead
│   │   └── settings.py          # AppSettings (Table) + Read/Update Schemas
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── httpclient.py        # fetch_page(), fetch_pages(), fetch_binary() mit curl-cffi
│   │   └── parser.py            # parse_search_results(), parse_ad_detail(), parse_next_page_urls()
│   └── services/
│       ├── __init__.py
│       ├── ai.py                # AIService: analyze_unprocessed(), Vergleichspreise, defensiver Prompt
│       ├── scraper.py           # ScraperService: scrape_adsearch() (Preview → Filter → Detail → Save)
│       └── settings.py          # get_setting(), DEFAULTS, is_setup_complete()
├── cli/
│   ├── __init__.py
│   ├── analyze.py               # uv run analyze [limit]
│   ├── reset_db.py              # uv run dbreset
│   ├── scrape.py                # uv run scrape [adsearch_id]
│   └── start.py                 # uv run start [--skip-tests]
├── tests/
│   ├── fixtures/ad.html
│   └── test_*.py
├── data/
│   ├── .gitkeep
│   └── schnappster.db
├── web/                         # Next.js Frontend (Static Export → web/out)
│   ├── app/, components/, lib/, ...
│   └── out/                     # von FastAPI ausgeliefert
├── .env                         # OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL
├── .gitignore
├── pyproject.toml               # Entry Points: dbreset, scrape, analyze, start
└── schnappster-context.md
```

## Datenmodelle

**AdSearch:** Suchauftrag (Name, URL, Intervall, Min/Max Preis, Blacklist, Prompt-Addition, is_active)
**Ad:** Einzelanzeige (Titel, Preis, Beschreibung, Bilder als comma-separated URLs, Standort PLZ/Stadt, Verkäufer-Info inkl. Rating 0-2, KI-Felder: bargain_score 0-10, ai_summary, ai_reasoning, is_analyzed)
**ScrapeRun:** Scrape-Protokoll (started_at, finished_at, ads_found, ads_new, status)
**ErrorLog:** Fehler-Protokoll (error_type, message, details)
**AppSettings:** Key-Value Store für Runtime-Settings

## Architektur-Prinzipien
- **scraper/**: Nur technische Infrastruktur (HTTP, HTML-Parsing)
- **services/**: Business-Logik (Orchestrierung, KI-Analyse)
- **api/**: HTTP-Endpoints, api_router in __init__.py gebündelt
- **core/**: DB, Settings, Scheduler, Logging – alles über core/__init__.py re-exportiert
- **cli/**: Entry Points (pyproject.toml), kein Shebang nötig
- **models/**: Table-Definition oben als Source of Truth, API-Schemas darunter (bewusste Duplizierung)
- Kein Alembic – bei Schema-Änderungen: uv run dbreset
- .env für Konfiguration statt DB-Settings für API Keys
- Absolute Pfade via get_app_root() statt relative Pfade

## Aktueller Stand
- Backend komplett funktional: Scraping, KI-Analyse, REST-API, Scheduler
- KI nutzt Vergleichspreise aus gleicher Suche + defensiven Prompt
- Bilder werden als Base64 an OpenRouter geschickt (Bildtyp via Magic Bytes erkannt)
- Frontend noch nicht gebaut (Prompt existiert als Spezifikation)

## Offene Punkte
- Frontend bauen (Vue 3 + shadcn-vue)
- services/settings.py evtl. aufräumen (teilweise durch .env ersetzt)
- Timezone-Handling (datetime.utcnow ist deprecated)
- Optional: n:m Beziehung Ad ↔ AdSearch