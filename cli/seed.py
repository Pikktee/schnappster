"""Füllt die Datenbank mit Beispieldaten für alle Tabellen.

Verwendung:
    uv run seed
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.core import db_engine, setup_logging
from app.models import AdSearch, AppSettings, ErrorLog, ScrapeRun

logger = logging.getLogger(__name__)


def main() -> None:
    """Fügt Beispieldaten in alle Datenbanktabellen ein."""
    setup_logging()

    past = datetime.now(UTC) - timedelta(hours=2)

    adsearch = AdSearch(
        owner_id="00000000-0000-0000-0000-000000000001",
        name="PodMic Frankfurt",
        url="https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250",
    )

    with Session(db_engine) as session:
        # Suchauftrag
        session.add(adsearch)
        session.flush()
        assert adsearch.id is not None
        search_id = adsearch.id

        # AppSettings (Beispielwerte)
        for key, value in [
            ("exclude_commercial_sellers", "false"),
            ("min_seller_rating", "1"),
            ("telegram_notifications_enabled", "false"),
            ("auto_delete_ads_days", "7"),
        ]:
            session.add(AppSettings(key=key, value=value))

        # ScrapeRun (ohne Anzeigen – werden beim Start vom Scraper gefüllt)
        session.add(
            ScrapeRun(
                adsearch_id=search_id,
                started_at=past,
                finished_at=past + timedelta(minutes=1),
                ads_found=0,
                ads_new=0,
            )
        )

        # ErrorLog (Beispiel-Fehler)
        for entry in [
            ErrorLog(
                adsearch_id=search_id,
                error_type="ScraperError",
                message="Connection timeout beim Abruf der Suchergebnisse.",
                details="requests.exceptions.ConnectTimeout: Max retries exceeded.",
            ),
            ErrorLog(
                adsearch_id=None,
                error_type="AnalysisError",
                message="OpenAI API returned 429 Too Many Requests.",
                details=None,
            ),
        ]:
            session.add(entry)

        session.commit()

    logger.info(
        "Seed completed: 1 AdSearch, 4 AppSettings, 1 ScrapeRun, 2 ErrorLogs "
        "(keine Ads – werden vom Scraper gefüllt)"
    )
