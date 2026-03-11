"""Background job scheduler for periodic scraping and AI analysis."""

import logging
import traceback
from datetime import datetime

from apscheduler.schedulers.background import (  # pyright: ignore[reportMissingImports]
    BackgroundScheduler,
)
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.db import db_engine
from app.models.ad import Ad
from app.models.errorlog import ErrorLog
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)


class BackgroundJobs:
    """Scheduler for scrape and analyzer jobs

    Note: Single-worker queues to avoid overlap.
    """

    _EXECUTORS = {
        "default": {"type": "threadpool", "max_workers": 1},  # Fallback
        "scraper": {"type": "threadpool", "max_workers": 1},
        "analyzer": {"type": "threadpool", "max_workers": 1},
    }

    def __init__(self) -> None:
        """Create the scheduler with threadpool executors for scraper and analyzer."""
        self._scheduler = BackgroundScheduler(executors=self._EXECUTORS)

    def start(self) -> None:
        """Start the scheduler and register periodic and one-off jobs."""

        # Periodic scrape job
        self._scheduler.add_job(
            self._run_scrape_ads,
            "interval",
            minutes=1,
            id="run_scrape_ads",
            replace_existing=True,
            executor="scraper",
        )

        # Initial scrape job (run once at startup)
        self._scheduler.add_job(
            self._run_scrape_ads,
            "date",
            id="initial_scrape",
            executor="scraper",
        )

        # Initial analyze job (run once at startup to process any backlog)
        self._scheduler.add_job(
            self._run_analyze_ads,
            "date",
            run_date=datetime.now(),
            id="initial_analyze",
            executor="analyzer",
        )

        self._scheduler.start()
        logger.info(
            "Scheduler started: scrape every 1 min (scraper queue), "
            "AI analysis after each scrape when new ads found and once at startup (analyzer queue)"
        )

    def stop(self) -> None:
        """Shut down the scheduler; no new jobs, running jobs may finish in background."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def trigger_scrape_once(self) -> None:
        """Queue a one-off scrape run (e.g. after creating a new ad search)."""
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
        """Job: run scrape_due_searches; queue analyzer if new ads found."""
        with Session(db_engine) as session:
            total_new = ScraperService(session).scrape_due_searches()

        # If new ads were found, queue AI analysis job
        if total_new > 0:
            self._scheduler.add_job(
                self._run_analyze_ads,
                "date",
                run_date=datetime.now(),
                executor="analyzer",
            )
            logger.info(f"Queued AI analysis after scraping {total_new} new ad(s)")

    def _run_analyze_ads(self) -> None:
        """Job: analyze unprocessed ads; re-queue if backlog remains and progress made."""
        with Session(db_engine) as session:
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
                pass  # API key not configured yet
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


# Modul-Level-Instanz → de facto Singleton
_jobs = BackgroundJobs()


def get_background_jobs() -> BackgroundJobs:
    """Return the shared BackgroundJobs instance (module-level singleton)."""
    return _jobs
