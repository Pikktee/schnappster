"""Hintergrund-Job-Scheduler für periodisches Scraping und KI-Auswertung."""

import logging
import traceback
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import (  # pyright: ignore[reportMissingImports]
    BackgroundScheduler,
)
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.core.db import db_engine
from app.models.ad import Ad
from app.models.logs_error import ErrorLog
from app.services.scraper import ScraperService
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)

ANALYZE_BATCH_SIZE = 10
ANALYZE_RETRY_DELAY_SECONDS = 60
ANALYZE_SAFETY_INTERVAL_MINUTES = 5
QUEUED_ANALYZE_JOB_ID = "queued_analyze_ads"
SCHEDULER_MISFIRE_GRACE_SECONDS = 60
STARTUP_JOB_DELAY_SECONDS = 2


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
        self._scheduler = BackgroundScheduler(executors=deepcopy(self._EXECUTORS))

    def start(self) -> None:
        """Startet den Scheduler und registriert periodische und einmalige Jobs."""
        startup_run_date = datetime.now(UTC) + timedelta(seconds=STARTUP_JOB_DELAY_SECONDS)

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
            run_date=startup_run_date,
            id="initial_scrape",
            executor="scraper",
            misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
        )

        # Erster Analyse-Job (einmalig beim Start, verarbeitet Rückstand)
        self._scheduler.add_job(
            self._run_analyze_ads,
            "date",
            run_date=startup_run_date,
            id="initial_analyze",
            executor="analyzer",
            misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
        )

        # Sicherheitsnetz: verarbeitet Rückstände auch dann, wenn ein One-off-Trigger ausfällt.
        self._scheduler.add_job(
            self._run_analyze_ads,
            "interval",
            minutes=ANALYZE_SAFETY_INTERVAL_MINUTES,
            id="run_analyze_ads",
            replace_existing=True,
            executor="analyzer",
            misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
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
            run_date=startup_run_date,
            id="initial_cleanup",
            executor="default",
            misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
        )

        self._scheduler.start()
        logger.info(
            "Scheduler started: scrape every 1 min (scraper queue), "
            "AI analysis after each scrape when new ads found, once at startup, "
            f"and every {ANALYZE_SAFETY_INTERVAL_MINUTES} min as backlog safety net, "
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
            run_date=datetime.now(UTC),
            id="trigger_scrape_once",
            replace_existing=True,
            executor="scraper",
            misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
        )
        logger.debug("Queued one-off scrape run")

    def _queue_analyze_ads(self, delay_seconds: int = 0) -> None:
        """Stellt einen Analyzer-Lauf in die Queue, dedupliziert aber wartende Retries."""
        job_kwargs = {
            "id": QUEUED_ANALYZE_JOB_ID,
            "replace_existing": True,
            "executor": "analyzer",
            "misfire_grace_time": SCHEDULER_MISFIRE_GRACE_SECONDS,
        }
        if delay_seconds > 0:
            job_kwargs["run_date"] = datetime.now(UTC) + timedelta(seconds=delay_seconds)

        self._scheduler.add_job(self._run_analyze_ads, "date", **job_kwargs)

    def _run_scrape_ads(self) -> None:
        """Job: scrape_due_searches ausführen; bei neuen Anzeigen Analyzer in die Queue."""
        with Session(db_engine) as session:
            total_new = ScraperService(session).scrape_due_searches()

        # Bei neuen Anzeigen KI-Analyse anstoßen
        if total_new > 0:
            self._queue_analyze_ads()
            logger.info(f"Queued AI analysis after scraping {total_new} new ad(s)")

    def _run_analyze_ads(self) -> None:
        """Job: unbearbeitete Anzeigen analysieren; bei Rückstand erneut einplanen."""
        with Session(db_engine) as session:
            run_ok = False
            analyzed = 0
            try:
                from app.services.ai import AIService

                ai_service = AIService(session)
                analyzed = ai_service.analyze_unprocessed(limit=ANALYZE_BATCH_SIZE)
                run_ok = True
                if analyzed > 0:
                    logger.info(f"AI analyzed {analyzed} ads")
            except ValueError:
                pass  # API-Key noch nicht konfiguriert
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                try:
                    session.add(
                        ErrorLog(
                            adsearch_id=None,
                            error_type="AIAnalysisError",
                            message=str(e),
                            details=traceback.format_exc(),
                        )
                    )
                    session.commit()
                except Exception:
                    logger.exception("Failed to persist AI analysis job error")
                self._queue_analyze_ads(delay_seconds=ANALYZE_RETRY_DELAY_SECONDS)

            if run_ok:
                remaining_query = select(Ad).where(
                    Ad.is_analyzed.is_(False)  # pyright: ignore[reportAttributeAccessIssue]
                )
                remaining = session.exec(
                    select(func.count()).select_from(remaining_query.subquery())
                ).one()
                if remaining <= 0:
                    return

                if analyzed <= 0:
                    self._queue_analyze_ads(delay_seconds=ANALYZE_RETRY_DELAY_SECONDS)
                    logger.warning(
                        "AI analysis made no progress; retrying in %s seconds (%s ads remaining)",
                        ANALYZE_RETRY_DELAY_SECONDS,
                        remaining,
                    )
                    return

                self._queue_analyze_ads()
                logger.debug(f"Queued next AI analysis ({remaining} ads remaining)")

    def _run_cleanup_old_ads(self) -> None:
        """Job: Anzeigen löschen, die älter als die konfigurierte Anzahl Tage sind."""
        with Session(db_engine) as session:
            days = SettingsService(session).get_int("auto_delete_ads_days")
            if days == 0:
                logger.debug("Auto-delete disabled (auto_delete_ads_days=0)")
                return

            cutoff = datetime.now(UTC) - timedelta(days=days)
            result = session.execute(delete(Ad).where(Ad.first_seen_at < cutoff))
            deleted = result.rowcount or 0
            if deleted <= 0:
                logger.debug(f"Cleanup: no ads older than {days} days")
                return

            session.commit()
            logger.info(f"Cleanup: deleted {deleted} ad(s) older than {days} days")


# Modul-Level-Instanz → de facto Singleton
_jobs = BackgroundJobs()


def get_background_jobs() -> BackgroundJobs:
    """Gibt die gemeinsame BackgroundJobs-Instanz zurück (Modul-Singleton)."""
    return _jobs
