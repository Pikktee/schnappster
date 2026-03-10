# Schnappster – Development Context

## Project Overview

**Schnappster** is a personal web application that periodically scrapes search results from [Kleinanzeigen.de](https://www.kleinanzeigen.de), analyzes listings for bargains using AI (OpenRouter API), and displays results in a dashboard.

### Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.13, FastAPI, SQLModel, SQLite |
| **Scraping** | curl-cffi (HTTP), BeautifulSoup4 (parsing) |
| **AI** | OpenRouter API (LLM analysis) |
| **Scheduling** | APScheduler (background jobs) |
| **Frontend** | Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (static export) |
| **Tooling** | uv (package manager), Ruff (linting), Pyright (type checking), pytest |

## Project Structure

```
schnappster/
├── app/
│   ├── main.py                  # FastAPI app with lifespan (init_db, BackgroundJobs)
│   ├── routes/                     # FastAPI routers (bundled via routes/__init__.py)
│   │   ├── ads.py               # GET /api/ads/, GET /api/ads/{id}
│   │   ├── adsearch.py          # CRUD /api/adsearches/
│   │   ├── errorlogs.py         # GET /api/errorlogs/
│   │   ├── scraperuns.py        # GET /api/scraperuns/
│   │   └── settings.py          # GET/PUT /api/settings/
│   ├── core/                    # Infrastructure (DB, settings, background jobs, logging)
│   │   ├── db.py                # SQLModel engine, DbSession, init_db()
│   │   ├── settings.py          # Pydantic settings (.env), get_app_root()
│   │   ├── background_jobs.py   # APScheduler: scrape (1min + startup), analyze (startup + after scrape; re-queue until backlog empty)
│   │   └── logging.py           # RichHandler setup
│   ├── models/                  # SQLModel tables + API schemas
│   │   ├── ad.py                # Ad table + AdRead schema
│   │   ├── adsearch.py          # AdSearch table + CRUD schemas
│   │   ├── errorlog.py          # ErrorLog table + schema
│   │   ├── scraperun.py         # ScrapeRun table + schema
│   │   └── settings.py          # AppSettings table + schemas
│   ├── scraper/                 # HTTP/HTML layer (no business logic)
│   │   ├── httpclient.py        # fetch_page(), fetch_pages(), fetch_binary()
│   │   └── parser.py            # parse_search_results(), parse_ad_detail()
│   └── services/                # Business logic
│       ├── ai.py                # AIService: analyze_unprocessed() with OpenRouter
│       ├── scraper.py           # ScraperService: scrape_adsearch() pipeline
│       ├── settings.py          # SettingsService: get_setting(), DEFAULTS
│       └── telegram.py          # TelegramService: send_bargain_notification()
├── cli/                         # Entry points (no shebangs needed)
│   ├── start.py                 # uv run start [--dev] [--skip-tests]
│   ├── scrape.py                # uv run scrape [adsearch_id]
│   ├── analyze.py               # uv run analyze [limit]
│   └── dbreset.py               # uv run dbreset
├── tests/                       # pytest tests
├── web/                         # Next.js frontend (static export → web/out/)
├── data/                        # SQLite database (schnappster.db)
├── .env                         # API keys (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL, etc.)
└── pyproject.toml               # Dependencies, scripts, tool config
```

## Building and Running

### Package Manager

This project uses **uv** as the package manager.

```bash
uv sync          # Install dependencies
uv run <cmd>     # Run commands in virtual environment
```

### Backend Commands

```bash
# Start the application (runs tests first, builds frontend)
uv run start

# Start without running tests
uv run start --skip-tests

# Development mode (Next.js dev server + backend with hot reload)
uv run start --dev

# Manual scraping trigger
uv run scrape [adsearch_id]

# Manual AI analysis trigger
uv run analyze [limit]

# Reset database (drops and recreates - no Alembic migrations)
uv run dbreset
```

### Frontend Commands

```bash
cd web

# Development server (proxies API to localhost:8000)
npm run dev

# Static export to web/out/ (served by FastAPI)
npm run export

# Linting
npm run lint
```

### Testing and Quality

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_parser.py

# Lint with Ruff
uv run ruff check .

# Format with Ruff
uv run ruff format .

# Type check with Pyright
pyright
```

## Architecture Principles

### Layer Responsibilities

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **core/** | Infrastructure: DB engine, settings, background jobs, logging | Re-exported via `core/__init__.py` |
| **models/** | SQLModel table definitions + API schemas | Re-exported via `models/__init__.py` |
| **scraper/** | Pure HTTP/HTML layer (no business logic) | `httpclient.py`, `parser.py` |
| **services/** | Business logic: orchestration, AI analysis | `ScraperService`, `AIService`, `SettingsService` |
| **routes/** | FastAPI routers | Bundled via `routes/__init__.py` into `api_router` |
| **cli/** | Entry points defined in `pyproject.toml` | No shebangs required |

### Scraping Pipeline (ScraperService)

1. Fetch search result pages (preview list)
2. Filter out already-known ads by `external_id`
3. Fetch detail pages in parallel
4. Apply filters: price range, blacklist keywords, seller type, seller rating
5. Save new ads to DB
6. AI analysis runs once at startup and after each scrape when new ads were found (queued on analyzer); each run processes up to 10 ads and re-queues if backlog remains; scraper and analyzer each have a single-worker queue.

### Scheduler (APScheduler BackgroundScheduler)

| Job | When | Description |
|-----|------|-------------|
| Scrape | 1 minute + once at startup | Scrapes all active `AdSearch` records that are due; when new ads found, queues AI analysis |
| Analyze | Once at startup + when queued after scrape | Processes up to 10 unprocessed ads; if backlog remains and progress made, queues next run (re-queue until empty) |

Both scrape and analyze use separate single-worker queues so they do not overlap.

### Frontend Architecture

- **Static export** (`web/out/`) served directly by FastAPI
- Dynamic detail routes (`/ads/[id]`, `/searches/[id]`) use fallback to id=0 shell, then client-side router fetches data
- `NEXT_PUBLIC_API_URL` env var controls API base URL (empty = same origin)

## Data Models

| Model | Description |
|-------|-------------|
| **AdSearch** | Search job (name, URL, interval, price range, blacklist, prompt addition, is_active) |
| **Ad** | Listing (title, price, description, images, location, seller info, AI fields: bargain_score, ai_summary, ai_reasoning) |
| **ScrapeRun** | Scrape log (started_at, finished_at, ads_found, ads_new, status) |
| **ErrorLog** | Error record (error_type, message, details) |
| **AppSettings** | Key-value store for runtime settings |

### Key Fields

- `Ad.bargain_score`: 0-10 (AI-assigned, conservative scale)
- `Ad.seller_rating`: 0-2 (0=poor, 1=ok, 2=top)
- `Ad.image_urls`: Comma-separated URLs
- `AppSettings`: Used for runtime-configurable settings (seller filters, Telegram, etc.)

## Key Conventions

- **No Alembic**: Schema changes require `uv run dbreset`
- **Database path**: `data/schnappster.db`, resolved via `get_app_root()` (never relative paths)
- **API keys**: Stored in `.env` (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL), not in DB
- **Absolute paths**: Always use `get_app_root()` instead of relative paths
- **Models**: Table definitions as source of truth, API schemas in same file (intentional duplication)
- **Re-exports**: `core/__init__.py` and `models/__init__.py` re-export all public symbols

## Environment Variables

Create a `.env` file with:

```
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=your_model_choice
OPENAI_BASE_URL=https://openrouter.ai/api/v1
TELEGRAM_BOT_TOKEN=optional_bot_token
TELEGRAM_CHAT_ID=optional_chat_id
```

## Development Practices

### Coding Style

- **Line length**: 100 characters (configured in `pyproject.toml`)
- **Linting rules**: E, F, I, N, UP, B, SIM, ASYNC (see `pyproject.toml`)
- **Type checking**: Pyright with Python 3.12 target
- **Formatting**: Ruff formatter

### Testing

- Tests located in `tests/` directory
- pytest with `asyncio_mode = "auto"`
- Fixtures in `tests/fixtures/`
- Run tests before starting app (unless `--skip-tests`)

### Git Workflow

- Database file (`data/schnappster.db`) is git-ignored
- `.env` file is git-ignored (create locally)
- Frontend build output (`web/out/`) is git-ignored

## Current Status

- ✅ Backend fully functional: Scraping, AI analysis, REST API, Scheduler
- ✅ AI uses comparison prices from same search + defensive prompt
- ✅ Images sent to OpenRouter as base64 (MIME type detected via magic bytes)
- ⏳ Frontend: Next.js static export served by FastAPI

## Known Technical Debt

- `services/settings.py` may need cleanup (partially replaced by `.env`)
- Timezone handling: `datetime.utcnow` is deprecated
- Optional: n:m relationship between Ad ↔ AdSearch
