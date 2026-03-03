# pyright: reportMissingImports=false
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.core.db import engine
from app.models.adsearch import AdSearch
from app.scraper.service import ScraperService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def check_and_scrape() -> None:
    """Check all active AdSearches and scrape those that are due."""
    with Session(engine) as session:
        searches = session.exec(select(AdSearch).where(AdSearch.is_active.is_(True))).all()

        logger.info(f"Found {len(searches)} active AdSearches")

        scraper = ScraperService(session)
        now = datetime.utcnow()

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


def _is_due(adsearch: AdSearch, now: datetime) -> bool:
    """Check if an AdSearch is due for scraping."""
    if adsearch.last_scraped_at is None:
        return True

    next_scrape = adsearch.last_scraped_at + timedelta(minutes=adsearch.scrape_interval_minutes)
    return now >= next_scrape


def start_scheduler() -> None:
    """Start the background scheduler, checking every minute."""
    scheduler.add_job(
        check_and_scrape,
        "interval",
        minutes=1,
        id="check_and_scrape",
        replace_existing=True,
    )
    # Initial scrape nach 5 Sekunden, damit der Server erst hochfährt
    scheduler.add_job(
        check_and_scrape,
        "date",
        id="initial_scrape",
    )
    scheduler.start()
    logger.info("Scheduler started: checking every minute for due scrapes")


def stop_scheduler() -> None:
    """Shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
