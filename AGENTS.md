# AGENTS.md / CLAUDE.md (symlink)

## What is Schnappster?

A personal web app that periodically scrapes Kleinanzeigen.de search results, analyzes them for bargains using AI (OpenAI-compatible API, e.g. OpenRouter or Alibaba Model Studio), and displays results in a dashboard.

## Commands

### Backend (Python)

Package manager is `uv`. CLI entry points are mostly in root `pyproject.toml`; **`mcp-server`** comes from the editable dependency **`schnappster-mcp`** (`mcp-server/pyproject.toml`).

```bash
uv run start              # Start FastAPI server (runs tests first)
uv run start --skip-tests # Start without running tests
uv run start --dev        # Dev mode: Next.js on :3000 (hot reload) + backend on :8000
uv run start --port 8080  # Custom port
uv run scrape [adsearch_id]  # Manually trigger a scrape
uv run analyze [limit]       # Manually trigger AI analysis
uv run dbreset               # Drop and recreate DB (no Alembic – use this for schema changes)
uv run docs [show]           # Generate API docs (pdoc), optionally open in browser
uv run seed                  # Seed database with sample data
uv run release               # Create a release
uv run release-chrome-extension  # Package Chrome extension to extensions/dist/
uv run mcp-server          # Remote MCP server (mcp-server package; same root .env)
uv run mcp-server --tunnel # Quick Tunnel + MCP; sets MCP_RESOURCE_SERVER_URL for child (no .env edit)

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

Static export → `web/out/`, served by FastAPI after `npm run build`. `NEXT_PUBLIC_API_URL`: empty = same origin. Optional: `NEXT_PUBLIC_MCP_ENDPOINT_URL` — öffentliche MCP-URL für die Hilfsseite `/mcp-connect` (Kopier-Button).

### Docker

```bash
docker compose up -d    # Uses proxy-net external network, SQLite volume mount
```

### Chrome Extension

Source: `extensions/chrome/`. Package: **`uv run release-chrome-extension`** → `extensions/dist/` (also listed under Backend commands).

### Remote MCP-Server (Streamable HTTP)

Separate Python project in **`mcp-server/`** — proxies tools to the Schnappster API with Supabase Bearer auth.

```bash
# vom Repo-Root (siehe auch: uv run mcp-server in der Befehlsliste oben)
uv run mcp-server   # default http://127.0.0.1:8766/mcp
uv run mcp-server --tunnel   # TryCloudflare + MCP (public URL in logs); or cloudflared manually + MCP_RESOURCE_SERVER_URL in .env

cd mcp-server && uv sync --all-groups && uv run schnappster-mcp   # nur Unterprojekt-venv
uv run pytest            # im Repo-Root (inkl. MCP-Regex-Tests gegen schnappster_mcp.cli)
cd mcp-server && uv run pytest   # nur Tests unter mcp-server/tests
cd mcp-server && uv run ruff check schnappster_mcp tests
```

## Architecture

### Backend layers

- **`app/core/`** — DB engine, settings (Pydantic `.env`), background jobs (APScheduler), logging. Everything re-exported via `core/__init__.py`.
- **`app/models/`** — SQLModel table definitions (source of truth) + API schemas (Read/Create/Update) in the same file. All re-exported via `models/__init__.py`.
- **`app/scraper/`** — Pure HTTP/HTML layer: `httpclient.py` (curl-cffi) and `parser.py` (BeautifulSoup). No business logic here.
- **`app/services/`** — Business logic: `ScraperService` orchestrates scraping pipeline, `AIService` handles AI analysis (OpenAI-compatible API) with comparison prices, `SettingsService` reads runtime settings from DB.
- **`app/routes/`** — FastAPI routers. All bundled via `routes/__init__.py` into `api_router`, which is included in `main.py`.
- **`cli/`** — Root CLI (`uv run <cmd>`). **`mcp-server`** / **`schnappster-mcp`** live in **`mcp-server/schnappster_mcp/`** (editable dependency).

### Scraping pipeline (ScraperService)

1. Fetch search result pages (preview list)
2. Filter out already-known ads by `external_id`
3. Fetch detail pages in parallel
4. Apply filters: price range, blacklist keywords, seller type, seller rating
5. Save new ads to DB
6. AI analysis runs after each scrape when new ads were found (queued on analyzer), and once at startup; each analyze run processes up to 10 ads and re-queues another run if backlog remains (until empty). Scraper and analyzer each have a single-worker queue so jobs run one after another without overlap.

### Scheduler (APScheduler, `core/background_jobs.py`, class `BackgroundJobs`)

- Scrape job runs every 1 minute and once at startup — loads active `AdSearch` records, scrapes those that are due via `ScraperService.scrape_due_searches()`; when new ads were scraped, queues one AI analysis run (separate single-worker queue so scrape and analyze never overlap).
- Analyze job runs once at startup (to process any backlog) and is queued after each scrape when new ads were found. Each run processes up to 10 unprocessed ads; if backlog remains and at least one ad was analyzed, another analyze run is queued (re-queue until backlog is empty).

### Frontend

Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (Radix UI). Build/dev workflow and `NEXT_PUBLIC_API_URL`: **Commands → Frontend** above.

- `web/lib/api.ts` — all API calls, typed against `web/lib/types.ts`
- `web/app/(app)/` — route group for the main app layout (sidebar)
- Dynamic detail routes (`/ads/[id]`, `/searches/[id]`) are handled by FastAPI serving the pre-rendered `id=0` shell as fallback, then the client router fetches actual data
- `web/components/ui/` — shadcn/ui primitives (don't modify directly)

### Key conventions

- **Database:** SQLite at `data/schnappster.db`, path via `get_app_root()` (never relative paths). No Alembic — schema changes → **`uv run dbreset`**.
- API keys (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`) live in `.env`, not the DB
- **`AppSettings`:** runtime-configurable settings (seller filters, Telegram, etc.)
- Image URLs stored as comma-separated strings in `Ad.image_urls`
- Seller rating is an int 0–2 (0=poor, 1=ok, 2=top)
- `bargain_score` is 0–10 (AI-assigned)
- Ruff: line-length 100, rules `E, F, I, N, UP, B, SIM, ASYNC`, ignore `UP017`
- Tests run with `asyncio_mode = "auto"`, fixtures in `tests/fixtures/`

## Code style

- Descriptive names — avoid cryptic abbreviations (`get_active_searches`, not `get_as`).
- Keep functions roughly **≤ ~20 lines**; split larger logic into helpers.
- Prefer **early return** over deep nesting.
- Remove dead code — do not leave large commented-out blocks.
- Use **named constants** for non-obvious numeric thresholds (e.g. batch sizes), not magic numbers scattered in code.
- Comments explain **why**, not what the next line obviously does.

## Python & FastAPI habits

- Full **type hints**; Pyright is used — avoid `Any` unless justified.
- Avoid `# type: ignore` except where unavoidable.
- **Thin routes:** validate input → call service → return response.
- Inject **services via `Depends()`**, not by constructing inside route bodies.
- Set **HTTP status codes** explicitly where it matters (`201`, `204`, …).
- Use **Pydantic / SQLModel** schemas for request and response bodies — avoid untyped `dict` payloads.
- Raise **`HTTPException`** with a clear `detail` string.
- **Async** for IO-bound work (HTTP, DB); **sync** for CPU-heavy pure logic when appropriate.

## Testing

- Prefer testing **observable behavior**, not private methods or implementation details.
- New services and filter logic should get **unit tests** (same spirit as `test_scraper_filters.py`).
- **`uv run pytest`** should stay green before merge.

## Output Format

- Begin every response with "━━━" on its own line to visually separate it from previous content
