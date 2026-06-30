# AGENTS.md / CLAUDE.md (symlink)

## What is Schnappster?

A personal web app that periodically scrapes Kleinanzeigen.de search results, analyzes them for bargains using AI (OpenAI-compatible API, e.g. OpenRouter or Alibaba Model Studio), and displays results in a dashboard. A second area, **Preis-Alarme** (price watches), monitors **arbitrary websites** for price changes and notifies via an in-app notification center and optional Telegram.

## Commands

### Backend (Python)

Package manager is `uv`. CLI entry points live in root `pyproject.toml` (inkl. **`mcp-server`** → `cli/mcp_server/cli.py`). Das Unterprojekt **`schnappster-mcp`** (`mcp-server/pyproject.toml`, editable) liefert **`schnappster-mcp`** / den Import **`schnappster_mcp`**.

```bash
uv run start              # Next.js on :3000 (hot reload) + FastAPI (runs tests first)
uv run start --skip-tests # Same without tests
uv run start --prod       # FastAPI only (no Next dev server; use ``cd web && npm run dev`` separately if needed)
uv run start --port 8080  # Custom backend port
uv run scrape [adsearch_id]  # Manually trigger a scrape
uv run analyze [limit]       # Manually trigger AI analysis
uv run dbreset               # Drop and recreate DB (no Alembic – use this for schema changes)
uv run createadmin [email] [pw]  # Create/promote an admin user (uses ADMIN_EMAIL/ADMIN_PASSWORD if omitted)
uv run docs [show]           # Generate API docs (pdoc), optionally open in browser
uv run seed                  # Seed database with sample data (creates a demo user as owner)
uv run release               # Create a release
uv run release-chrome-extension  # Package Chrome extension to extensions/dist/
uv run mcp-server              # TTY: Quick-Tunnel, URL einmal; ``r`` MCP neu, ``p`` Proxy, ``q`` Ende
uv run mcp-server --tunnel     # nur ohne TTY: TryCloudflare + MCP (ein Lauf)
uv run mcp-server --http-proxy # TTY: mitmdump von Anfang an; ``p`` schaltet Proxy; ohne TTY wie ``--tunnel``

uv run pytest                # Run all tests
uv run pytest tests/test_parser.py  # Run a single test file
uv run ruff check .          # Lint
uv run ruff format .         # Format
```

### Frontend (Next.js)

```bash
cd web
npm run dev     # Dev server (:3000); set ``NEXT_PUBLIC_API_URL`` to the API origin (e.g. http://127.0.0.1:8000)
npm run build   # Production build (Vercel uses this; ``npm start`` runs ``next start``)
npm run lint    # ESLint
```

Frontend and API are separate processes: locally ``uv run start`` starts both; production uses Vercel (web) + Railway (API). Set ``NEXT_PUBLIC_API_URL`` to the public API URL (e.g. ``https://api.<domain>``).

### Docker

```bash
docker compose up -d    # Uses proxy-net external network; ``DATABASE_URL`` in ``.env`` (SQLite-Datei; auf Railway persistentes Volume unter /data mounten)
```

### Chrome Extension

Source: `extensions/chrome/`. Package: **`uv run release-chrome-extension`** → `extensions/dist/` (also listed under Backend commands).

### Remote MCP-Server (Streamable HTTP)

Separate Python project in **`mcp-server/`** — proxies tools to the Schnappster API. **Auth: der mcp-server ist selbst ein OAuth-2.1-Authorization-Server** (`auth_server_provider` in `schnappster_mcp/server.py`, Logik in `core/oauth_provider.py`): Dynamic Client Registration, eigene Login-Seite unter `/oauth/login` (prüft E-Mail/Passwort gegen die API `POST /auth/login`), Authorization-Code-Flow mit PKCE. Das ausgegebene **Access-Token IST das App-JWT** der API; validiert wird es zustandslos per ``GET /users/me/`` (`ApiTokenVerifier`). Keine Refresh-Tokens — nach Ablauf des JWT (7 Tage) im Client neu verbinden. **Issuer = der mcp-server selbst** (`MCP_RESOURCE_SERVER_URL`-Origin), nicht die API; die Haupt-API stellt keine OAuth-Endpunkte.

```bash
# vom Repo-Root (siehe auch: uv run mcp-server in der Befehlsliste oben)
uv run mcp-server   # TTY: Quick-Tunnel + MCP (``r``/``p``/``q``); ohne TTY: lokaler MCP ohne Tunnel
uv run mcp-server --tunnel   # ohne TTY: TryCloudflare + MCP; im TTY ist der Tunnel ohnehin aktiv
uv run mcp-server --http-proxy   # mitmdump; Log unter logs/mcp_mitmdump_*.log (Pfad beim TTY-Start)

cd mcp-server && uv sync --all-groups && uv run schnappster-mcp   # nur Unterprojekt-venv
uv run pytest            # im Repo-Root (`tests/` + `cli/mcp_server/`, siehe `pytest.ini`)
cd mcp-server && uv run pytest   # nur `mcp-server/tests/` (eigenes Pytest-Projekt)
cd mcp-server && uv run ruff check schnappster_mcp tests
```

## Architecture

### Backend layers

- **`app/core/`** — DB engine, settings (Pydantic `.env`), background jobs (APScheduler), logging. Everything re-exported via `core/__init__.py`.
- **`app/models/`** — SQLModel table definitions (source of truth) + API schemas (Read/Create/Update) in the same file. All re-exported via `models/__init__.py`.
- **`app/scraper/`** — Pure HTTP/HTML layer: `httpclient.py` (curl-cffi) and `parser.py` (BeautifulSoup). No business logic here. The curl-cffi browser fingerprint is the `IMPERSONATE` constant (env `SCRAPE_IMPERSONATE`, default **`chrome131`**) — the library default `"chrome"` triggers Cloudflare 403s and Amazon price-stripped pages; `chrome131` passes both empirically from a residential IP. Override via env if a site needs a different fingerprint. **Optional proxy/unblocker** (env `SCRAPE_PROXY_URL`, plus `SCRAPE_PROXY_VERIFY=false` for MITM-cert proxies): when set, every request routes through it — needed because from a **datacenter IP (Railway) the fingerprint alone is not enough** (Amazon/Cloudflare penalise datacenter IPs regardless of fingerprint). Accepts a residential proxy or a scraping-API in proxy mode (`http://user:pass@host:port`). Empty = direct fetch (unchanged behaviour). Wired via `_REQUEST_EXTRA` into all three `session.get()` calls.
- **`app/services/`** — Business logic: `ScraperService` orchestrates scraping pipeline, `AIService` handles AI analysis (OpenAI-compatible API) with comparison prices, `SettingsService` reads runtime settings from DB. **`PriceExtractor`** (`price_extractor.py`) extracts price candidates from arbitrary HTML (JSON-LD → meta → visible text) and re-finds the chosen price via a stored locator; **`PriceWatchService`** runs the price-check pipeline; **`NotificationService`** manages the generic in-app notification store.
- **`app/routes/`** — FastAPI routers. All bundled via `routes/__init__.py` into `api_router`, which is included in `main.py`. Price-watch routes (`price_watches.py`, incl. `POST /price-watches/preview` for candidate extraction) and `notifications.py`.
- **`cli/`** — Root CLI (`uv run <cmd>`). Komfort-**`mcp-server`** (Tunnel-Supervisor, mitmproxy): **`cli/mcp_server/`**. **`schnappster-mcp`**: Python-Paket **`mcp-server/schnappster_mcp/`** (Import **`schnappster_mcp`**).

### Scraping pipeline (ScraperService)

1. Fetch search result pages (preview list)
2. Filter out already-known ads by `external_id`
3. Fetch detail pages in parallel
4. Apply filters: price range, blacklist keywords, seller type, seller rating
5. Save new ads to DB
6. AI analysis runs after each scrape when new ads were found (queued on analyzer), and once at startup; each analyze run processes up to 10 ads and re-queues another run if backlog remains (until empty). Scraper and analyzer each have a single-worker queue so jobs run one after another without overlap.

### Price-watch pipeline (PriceWatchService, `services/price_watch.py`)

1. **Create:** frontend `POST /price-watches/preview {url}` → backend fetches HTML (curl-cffi) → `PriceExtractor.extract_candidates()` (+ optional AI labels via `refine_with_ai`, falls back to heuristics without API key) → user picks one → `POST /price-watches/` stores the `PriceWatch` incl. the chosen **locator** (JSON: `jsonld`/`meta`/`css` strategy). For the `css` strategy the selector is **disambiguated** by anchoring to the nearest id/price-container ancestor (`_build_css_selector`) and the chosen value is stored in the locator — generic classes like Amazon's `span.a-offscreen` appear dozens of times, so a bare selector would re-find the wrong price.
2. **Monitor:** for each due watch, fetch HTML → `PriceExtractor.extract_price(html, locator)` → compare with `last_price`. On change, store a `PricePoint` (history only stores changes, not every check). If a `css` selector still matches multiple elements, `_disambiguate_css_match` picks the one closest to the stored value. Extraction failures set `last_error`/`consecutive_failures` (surfaced in the UI), not an exception.
3. **Alert:** with a threshold → alert when the price drops to/below it; without a threshold → alert on **any** price drop. Alerts create a `Notification` (+ optional Telegram via `notify_price_telegram`). Limitations (communicated in the wizard / surfaced as `last_error`): JS-rendered SPAs without structured/SEO data yield no price in the initial HTML; sites behind an active bot challenge (Cloudflare "Just a moment…") return a challenge page that an HTTP-only client cannot pass — `preview` detects these (`_looks_like_bot_challenge` / HTTP 403/429/503) and returns a clear 422 instead of a misleading "no prices found". **From Railway's datacenter IP, Amazon and Cloudflare block far more aggressively than a residential IP; the robust fix is to route fetches through a trusted IP via `SCRAPE_PROXY_URL` (see `app/scraper/` above) — without it, protected sites stay unreachable in prod regardless of fingerprint.**

### Scheduler (APScheduler, `core/background_jobs.py`, class `BackgroundJobs`)

- Scrape job runs every 1 minute and once at startup — loads active `AdSearch` records, scrapes those that are due via `ScraperService.scrape_due_searches()`; when new ads were scraped, queues one AI analysis run (separate single-worker queue so scrape and analyze never overlap).
- Analyze job runs once at startup (to process any backlog) and is queued after each scrape when new ads were found. Each run processes up to 10 unprocessed ads; if backlog remains and at least one ad was analyzed, another analyze run is queued (re-queue until backlog is empty).
- Price-check job runs every 1 minute and once at startup (own `pricewatch` single-worker queue) — checks due `PriceWatch` records via `PriceWatchService.check_due_watches()`. `trigger_price_check_once()` runs one immediately after a watch is created.

### Frontend

Next.js 16 + React 19 + Tailwind v4 + shadcn/ui (Radix UI). Build/dev workflow and `NEXT_PUBLIC_API_URL`: **Commands → Frontend** above.

- `web/lib/api.ts` — all API calls, typed against `web/lib/types.ts`
- `web/app/(app)/` — route group for the main app layout (sidebar)
- Dynamic detail routes (`/ads/[id]`, `/searches/[id]`, `/price-alerts/[id]`) are normal Next.js App Router pages; data is fetched in the browser from the API
- **Preis-Alarme:** `app/(app)/price-alerts/` (list + `[id]` detail with a `recharts` price-history chart); `price-watch-wizard.tsx` (URL → candidate selection → interval/threshold), `price-watch-card.tsx`. `notification-bell.tsx` in the header (`app/(app)/layout.tsx`) polls unread count. New page areas must be registered in `page-head-context.tsx` (title) and `app-page-head.tsx` (breadcrumb).
- `web/components/ui/` — shadcn/ui primitives (don't modify directly)

### Key conventions

- **Database:** SQLite by default (`DATABASE_URL=sqlite:///./data/schnappster.db`; PostgreSQL still accepted). WAL + `foreign_keys=ON` via PRAGMA in `app/core/db.py`. No Alembic — structural schema changes → **`uv run dbreset`** (drop all tables + `init_db()`). **Backwards-compatible column additions** are handled without data loss by `_apply_additive_columns()` in `init_db()` (list in `_ADDITIVE_COLUMNS`, `ALTER TABLE ADD COLUMN`, idempotent) — so prod (Railway SQLite volume) migrates on startup without `dbreset`.
- **Auth:** eigene JWT-Auth (kein Supabase). `JWT_SECRET` (required) signiert HS256-Tokens; `get_current_user` in `app/core/auth.py` dekodiert lokal und lädt den `User`. Mandantentrennung über `owner_id`-Filter im App-Code (keine DB-RLS). Registrierung legt inaktive Konten an; Admin schaltet frei. Erst-Admin via `uv run createadmin` oder `ADMIN_EMAIL`/`ADMIN_PASSWORD` beim Start.
- API keys (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`) and `JWT_SECRET` live in `.env`, not the DB
- **Passwords:** bcrypt-hash in `User.password_hash` (`app/core/security.py`); Policy: ≥8 Zeichen, Groß-/Kleinbuchstabe, Sonderzeichen
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
- **`uv run pytest`** (Root) und **`cd mcp-server && uv run pytest`** should stay green before merge. Root-**`pytest.ini`**: **`testpaths = tests cli/mcp_server`** — `mcp-server/tests/` wird separat gesammelt (**`mcp-server/pyproject.toml`** → `testpaths`), weil sonst zwei Ordner `tests/` als dasselbe Python-Paket `tests.*` kollidieren. Gemeinsame MCP-Fixtures: **`mcp-server/conftest.py`** (nicht unter `mcp-server/tests/`), damit `tests.conftest` nur im jeweiligen Pytest-Lauf jeweils einmal vorkommt.
- **DB-Tests (Root):** laufen gegen **In-Memory-SQLite** (`StaticPool`, frisches Schema pro Test) — kein Docker/Postgres nötig. Fixtures in `tests/conftest.py`: `client` (Admin-Override), `api_client` (echte JWT-Auth), `session`, `make_user`. `DATABASE_URL`/`JWT_SECRET` werden für die Collection per Default gesetzt.

## Output Format

- Begin every response with "━━━" on its own line to visually separate it from previous content
