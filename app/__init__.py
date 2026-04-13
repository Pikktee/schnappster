"""Schnappster-Anwendungspaket.

Schnappster ist eine persönliche Web-App, die periodisch Kleinanzeigen.de-Suchergebnisse scraped,
sie per KI (OpenAI-kompatible API) auf Schnäppchen prüft und die Ergebnisse in einem Dashboard
anzeigt.

Projektstruktur (Backend)
-------------------------
- **core/** — DB-Engine, Einstellungen (Pydantic/.env), Hintergrund-Jobs (APScheduler), Logging
- **models/** — SQLModel-Tabellen + API-Schemas (Read/Create/Update)
- **scraper/** — HTTP/HTML-Schicht (curl-cffi, BeautifulSoup), keine Geschäftslogik
- **services/** — Geschäftslogik: ScraperService (Pipeline), AIService (Analyse), SettingsService
- **routes/** — FastAPI-Router, gebündelt in api_router (main.py)
- **cli/** — Einstiegspunkte (uv run …)
"""
