"""Insert dummy error log entries for testing the Logs/Fehler list.

Usage:
    uv run seed-errorlogs
"""

import logging

from sqlmodel import Session, text

from app.core import db_engine, setup_logging
from app.models.errorlog import ErrorLog

logger = logging.getLogger(__name__)


def main() -> None:
    """Insert a few dummy ErrorLog rows into the database."""
    setup_logging()

    dummies = [
        ErrorLog(
            adsearch_id=None,
            error_type="ScraperError",
            message="Connection timeout beim Abruf der Suchergebnisse (Kleinanzeigen.de nicht erreichbar).",
            details="requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='www.kleinanzeigen.de', port=443): Max retries exceeded.\n  at fetch_search_page() in scraper/httpclient.py:42",
        ),
        ErrorLog(
            adsearch_id=None,
            error_type="AnalysisError",
            message="OpenAI API returned 429 Too Many Requests. Rate limit exceeded.",
            details=None,
        ),
        ErrorLog(
            adsearch_id=None,
            error_type="ParseError",
            message="Unerwartete HTML-Struktur: Detailseite enthält kein Preis-Element.",
            details="BeautifulSoup could not find element with selector '.price'.\nAd URL: https://www.kleinanzeigen.de/s-anzeige/123456789",
        ),
        ErrorLog(
            adsearch_id=None,
            error_type="ConfigError",
            message="OPENAI_API_KEY ist nicht gesetzt. Bitte .env prüfen.",
            details=None,
        ),
    ]

    with Session(db_engine) as session:
        session.execute(text("PRAGMA foreign_keys=ON"))
        for entry in dummies:
            session.add(entry)
        session.commit()
        logger.info("Added %d dummy error log entries", len(dummies))
