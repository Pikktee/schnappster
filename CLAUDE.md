# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Schnappster?

A personal web app that periodically scrapes Kleinanzeigen.de search results, analyzes them for bargains using AI (OpenRouter API), and displays results in a dashboard.

## Commands

### Backend (Python)

Package manager is `uv`. All Python entry points are defined in `pyproject.toml`.

```bash
uv run start          # Start FastAPI server (also runs tests first)
uv run start --skip-tests  # Start without running tests
uv run scrape [adsearch_id]  # Manually trigger a scrape
uv run analyze [limit]       # Manually trigger AI analysis
uv run dbreset               # Drop and recreate DB (no Alembic – use this for schema changes)

uv run pytest                # Run all tests
uv run pytest tests/test_parser.py  # Run a single test file
uv run ruff check .          # Lint
uv run ruff format .         # Format
```

### Frontend (Next.js)

```bash
cd web
npm run dev     # Dev server (proxies API to localhost:8000)
npm run build   # Static export to web/out/ (served by FastAPI)
npm run lint    # ESLint
```

The frontend is a **static export** (`web/out/`) served directly by FastAPI. After `npm run build`, FastAPI serves the output from `web/out/`. The `NEXT_PUBLIC_API_URL` env var controls the API base URL (empty = same origin).

## Architecture

### Backend layers

- **`app/core/`** — DB engine, settings (Pydantic `.env`), APScheduler, logging. Everything re-exported via `core/__init__.py`.
- **`app/models/`** — SQLModel table definitions (source of truth) + API schemas (Read/Create/Update) in the same file. All re-exported via `models/__init__.py`.
- **`app/scraper/`** — Pure HTTP/HTML layer: `httpclient.py` (curl-cffi) and `parser.py` (BeautifulSoup). No business logic here.
- **`app/services/`** — Business logic: `ScraperService` orchestrates scraping pipeline, `AIService` handles OpenRouter analysis with comparison prices, `SettingsService` reads runtime settings from DB.
- **`app/api/`** — FastAPI routers. All bundled via `api/__init__.py` into `api_router`, which is included in `main.py`.
- **`cli/`** — Entry points (`uv run <cmd>`). No shebangs needed.

### Scraping pipeline (ScraperService)

1. Fetch search result pages (preview list)
2. Filter out already-known ads by `external_id`
3. Fetch detail pages in parallel
4. Apply filters: price range, blacklist keywords, seller type, seller rating
5. Save new ads to DB
6. AI analysis runs separately every 2 minutes via scheduler

### Scheduler (APScheduler BackgroundScheduler)

- `check_and_scrape` runs every 1 minute — checks all active `AdSearch` records and scrapes those that are due based on `scrape_interval_minutes`
- `analyze_ads` runs every 2 minutes — processes up to 10 unanalyzed ads with AI
- Both also run once immediately on startup

### Frontend

Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (Radix UI). Static export served by FastAPI.

- `web/lib/api.ts` — all API calls, typed against `web/lib/types.ts`
- `web/app/(app)/` — route group for the main app layout (sidebar)
- Dynamic detail routes (`/ads/[id]`, `/searches/[id]`) are handled by FastAPI serving the pre-rendered `id=0` shell as fallback, then the client router fetches actual data
- `web/components/ui/` — shadcn/ui primitives (don't modify directly)

### Key conventions

- No Alembic — schema changes require `uv run dbreset`
- DB stored at `data/schnappster.db`, path resolved via `get_app_root()` (never relative paths)
- API keys (`OPENROUTER_API_KEY`, `OPENROUTER_AI_MODEL`) live in `.env`, not the DB
- `AppSettings` table used for runtime-configurable settings (seller filters, Telegram, etc.)
- Image URLs stored as comma-separated strings in `Ad.image_urls`
- Seller rating is an int 0–2 (0=poor, 1=ok, 2=top)
- `bargain_score` is 0–10 (AI-assigned)
