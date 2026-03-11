"""Schnappster application package.

Schnappster is a personal web app that periodically scrapes Kleinanzeigen.de search results,
analyses them for bargains using AI (OpenAI-compatible API), and displays results in a dashboard.

Project structure (backend)
----------------------------
- **core/** — DB engine, settings (Pydantic/.env), background jobs (APScheduler), logging
- **models/** — SQLModel tables + API schemas (Read/Create/Update)
- **scraper/** — HTTP/HTML layer (curl-cffi, BeautifulSoup), no business logic
- **services/** — Business logic: ScraperService (pipeline), AIService (analysis), SettingsService
- **routes/** — FastAPI routers, bundled in api_router (main.py)
- **cli/** — Entry points (uv run …)
"""

