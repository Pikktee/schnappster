"""Füllt die Datenbank mit Beispieldaten für alle Tabellen.

Verwendung:
    uv run seed
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.core import db_engine, setup_logging
from app.core.security import hash_password
from app.models import AdSearch, AppSettings, ErrorLog, ScrapeRun, User

logger = logging.getLogger(__name__)

_SEED_EMAIL = "demo@schnappster.local"
_SEED_PASSWORD = "Demo1234!"  # noqa: S105 — nur lokale Beispieldaten


def main() -> None:
    """Fügt Beispieldaten in alle Datenbanktabellen ein."""
    setup_logging()

    past = datetime.now(UTC) - timedelta(hours=2)

    with Session(db_engine) as session:
        # Demo-Benutzer (freigeschaltet) als Eigentümer der Beispieldaten
        seed_user = session.exec(select(User).where(User.email == _SEED_EMAIL)).first()
        if seed_user is None:
            seed_user = User(
                email=_SEED_EMAIL,
                password_hash=hash_password(_SEED_PASSWORD),
                role="admin",
                is_active=True,
                display_name="Demo",
            )
            session.add(seed_user)
            session.flush()
        owner_id = seed_user.id

        adsearch = AdSearch(
            owner_id=owner_id,
            name="PodMic Frankfurt",
            url="https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250",
        )

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
