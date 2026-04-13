"""Hintergrund-Job-Scheduler für periodisches Scraping und KI-Auswertung."""

import logging
import traceback
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import (  # pyright: ignore[reportMissingImports]
    BackgroundScheduler,
)
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.db import bg_engine
from app.models.ad import Ad
from app.models.logs_error import ErrorLog
from app.services.scraper import ScraperService
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)


class BackgroundJobs:
    """Scheduler für Scrape- und Analyzer-Jobs.

    Einzelne Worker-Queues, damit sich Jobs nicht überlappen.
    """

    _EXECUTORS = {
        "default": {"type": "threadpool", "max_workers": 1},  # Fallback
        "scraper": {"type": "threadpool", "max_workers": 1},
        "analyzer": {"type": "threadpool", "max_workers": 1},
    }

    def __init__(self) -> None:
        """Erstellt den Scheduler mit Threadpool-Executors für Scraper und Analyzer."""
        self._scheduler = BackgroundScheduler(executors=self._EXECUTORS)

    def start(self) -> None:
        """Startet den Scheduler und registriert periodische und einmalige Jobs."""

        # Periodischer Scrape-Job
        self._scheduler.add_job(
            self._run_scrape_ads,
            "interval",
            minutes=1,
            id="run_scrape_ads",
            replace_existing=True,
            executor="scraper",
        )

        # Erster Scrape-Job (einmalig beim Start)
        self._scheduler.add_job(
            self._run_scrape_ads,
            "date",
            id="initial_scrape",
            executor="scraper",
        )

        # Erster Analyse-Job (einmalig beim Start, verarbeitet Rückstand)
        self._scheduler.add_job(
            self._run_analyze_ads,
            "date",
            run_date=datetime.now(),
            id="initial_analyze",
            executor="analyzer",
        )

        # Periodischer Aufräum-Job (alle 24 Stunden)
        self._scheduler.add_job(
            self._run_cleanup_old_ads,
            "interval",
            hours=24,
            id="run_cleanup_old_ads",
            replace_existing=True,
            executor="default",
        )

        # Erster Aufräum-Job (einmalig beim Start)
        self._scheduler.add_job(
            self._run_cleanup_old_ads,
            "date",
            id="initial_cleanup",
            executor="default",
        )

        self._scheduler.start()
        logger.info(
            "Scheduler started: scrape every 1 min (scraper queue), "
            "AI analysis after each scrape when new ads found and once at startup, "
            "cleanup old ads every 24h and once at startup"
        )

    def stop(self) -> None:
        """Fährt Scheduler herunter; keine neuen Jobs, laufende Jobs können im Hintergrund enden."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def trigger_scrape_once(self) -> None:
        """Stellt einmaligen Scrape-Lauf in die Queue (z. B. nach Anlegen einer neuen Suche)."""
        self._scheduler.add_job(
            self._run_scrape_ads,
            "date",
            run_date=datetime.now(),
            id="trigger_scrape_once",
            replace_existing=True,
            executor="scraper",
        )
        logger.debug("Queued one-off scrape run")

    def _run_scrape_ads(self) -> None:
        """Job: scrape_due_searches ausführen; bei neuen Anzeigen Analyzer in die Queue."""
        with Session(bg_engine) as session:
            total_new = ScraperService(session).scrape_due_searches()

        # Bei neuen Anzeigen KI-Analyse anstoßen
        if total_new > 0:
            self._scheduler.add_job(
                self._run_analyze_ads,
                "date",
                run_date=datetime.now(),
                executor="analyzer",
            )
            logger.info(f"Queued AI analysis after scraping {total_new} new ad(s)")

    def _run_analyze_ads(self) -> None:
        """Job: unbearbeitete Anzeigen analysieren; bei Rückstand erneut einplanen."""
        with Session(bg_engine) as session:
            run_ok = False
            analyzed = 0
            try:
                from app.services.ai import AIService

                ai_service = AIService(session)
                analyzed = ai_service.analyze_unprocessed(limit=10)
                run_ok = True
                if analyzed > 0:
                    logger.info(f"AI analyzed {analyzed} ads")
            except ValueError:
                pass  # API-Key noch nicht konfiguriert
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                session.add(
                    ErrorLog(
                        adsearch_id=None,
                        error_type="AIAnalysisError",
                        message=str(e),
                        details=traceback.format_exc(),
                    )
                )
                session.commit()

            if run_ok:
                remaining_query = select(Ad).where(
                    Ad.is_analyzed.is_(False)  # pyright: ignore[reportAttributeAccessIssue]
                )
                remaining = session.exec(
                    select(func.count()).select_from(remaining_query.subquery())
                ).one()
                if remaining > 0 and analyzed > 0:
                    self._scheduler.add_job(
                        self._run_analyze_ads,
                        "date",
                        run_date=datetime.now(),
                        executor="analyzer",
                    )
                    logger.debug(f"Queued next AI analysis ({remaining} ads remaining)")

    def _run_cleanup_old_ads(self) -> None:
        """Job: Anzeigen löschen, die älter als die konfigurierte Anzahl Tage sind."""
        with Session(bg_engine) as session:
            days = SettingsService(session).get_int("auto_delete_ads_days")
            if days == 0:
                logger.debug("Auto-delete disabled (auto_delete_ads_days=0)")
                return

            cutoff = datetime.now(UTC) - timedelta(days=days)
            old_ads = session.exec(select(Ad).where(Ad.first_seen_at < cutoff)).all()

            if not old_ads:
                logger.debug(f"Cleanup: no ads older than {days} days")
                return

            for ad in old_ads:
                session.delete(ad)
            session.commit()
            logger.info(f"Cleanup: deleted {len(old_ads)} ad(s) older than {days} days")


# Modul-Level-Instanz → de facto Singleton
_jobs = BackgroundJobs()


def get_background_jobs() -> BackgroundJobs:
    """Gibt die gemeinsame BackgroundJobs-Instanz zurück (Modul-Singleton)."""
    return _jobs
