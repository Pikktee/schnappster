import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import (  # pyright: ignore[reportMissingImports]
    BackgroundScheduler,
)
from sqlmodel import Session, col, select

from app.core.db import engine
from app.models.adsearch import AdSearch
from app.services.scraper import ScraperService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def check_and_scrape() -> None:
    """Check all active AdSearches and scrape those that are due."""
    with Session(engine) as session:
        searches = session.exec(select(AdSearch).where(col(AdSearch.is_active).is_(True))).all()

        logger.info(f"Found {len(searches)} active AdSearches")

        scraper = ScraperService(session)
        now = datetime.now(UTC)

        for adsearch in searches:
            logger.info(
                f"Checking '{adsearch.name}': last_scraped={adsearch.last_scraped_at}, "
                f"interval={adsearch.scrape_interval_minutes}min, due={_is_due(adsearch, now)}"
            )
            if _is_due(adsearch, now):
                try:
                    logger.info(f"Scraping '{adsearch.name}'...")
                    scrape_run = scraper.scrape_adsearch(adsearch)
                    logger.info(
                        f"Done '{adsearch.name}': {scrape_run.ads_found} found, "
                        f"{scrape_run.ads_new} new"
                    )
                except Exception as e:
                    logger.error(f"Failed '{adsearch.name}': {e}")


def analyze_ads() -> None:
    """Analyze unprocessed ads with AI."""
    with Session(engine) as session:
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


def _is_due(adsearch: AdSearch, now: datetime) -> bool:
    """Check if an AdSearch is due for scraping."""
    if adsearch.last_scraped_at is None:
        return True

    next_scrape = adsearch.last_scraped_at + timedelta(minutes=adsearch.scrape_interval_minutes)
    return now >= next_scrape


def start_scheduler() -> None:
    """Start the background scheduler."""
    scheduler.add_job(
        check_and_scrape,
        "interval",
        minutes=1,
        id="check_and_scrape",
        replace_existing=True,
    )
    scheduler.add_job(
        analyze_ads,
        "interval",
        minutes=2,
        id="analyze_ads",
        replace_existing=True,
    )
    scheduler.add_job(
        check_and_scrape,
        "date",
        id="initial_scrape",
    )
    scheduler.start()
    logger.info("Scheduler started: scraping every minute, AI analysis every 2 minutes")


def stop_scheduler() -> None:
    """Shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
