import logging
import traceback
from datetime import datetime

from apscheduler.schedulers.background import (  # pyright: ignore[reportMissingImports]
    BackgroundScheduler,
)
from sqlmodel import Session

from app.core.db import db_engine
from app.models.errorlog import ErrorLog
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)


class BackgroundJobs:
    """
    Background job scheduler for scraping and AI analysis.
    """

    _EXECUTORS = {
        "default": {"type": "threadpool", "max_workers": 1},  # Fallback
        "scraper": {"type": "threadpool", "max_workers": 1},
        "analyzer": {"type": "threadpool", "max_workers": 1},
    }

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(executors=self._EXECUTORS)

    def start(self) -> None:
        """
        Start the scheduler and register jobs.
        """

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

        self._scheduler.start()
        logger.info(
            "Scheduler started: scrape every 1 min (scraper queue), "
            "AI analysis after each scrape when new ads found (analyzer queue)"
        )

    def stop(self) -> None:
        """
        Shut down the scheduler. Does not wait for running jobs; no new jobs
        will be started. Running jobs may still complete in the background
        until the process exits.
        """
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def _run_scrape_ads(self) -> None:
        """
        JOB: Check all active AdSearches and scrape those that are due.
        """
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
        """
        JOB: Analyze unprocessed ads with AI.
        """
        with Session(db_engine) as session:
            try:
                from app.services.ai import AIService

                ai_service = AIService(session)
                analyzed = ai_service.analyze_unprocessed(limit=10)
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
