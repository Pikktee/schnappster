"""Manual scraper invocation.

Usage:
    uv run scrape           # scrape all active AdSearches
    uv run scrape 1         # scrape AdSearch with ID 1
"""

import logging
import sys

from sqlmodel import Session, col, select

from app.core import db_engine, setup_logging
from app.models import AdSearch
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    adsearch_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with Session(db_engine) as session:
        if adsearch_id:
            adsearch = session.get(AdSearch, adsearch_id)
            if not adsearch:
                logger.error(f"AdSearch with ID {adsearch_id} not found")
                sys.exit(1)
            searches = [adsearch]
        else:
            searches = list(
                session.exec(select(AdSearch).where(col(AdSearch.is_active).is_(True))).all()
            )

        if not searches:
            logger.info("No active AdSearches found")
            return

        scraper = ScraperService(session)
        for adsearch in searches:
            logger.info(f"Scraping '{adsearch.name}'...")
            scrape_run = scraper.scrape_adsearch(adsearch)
            logger.info(
                f"Done: {scrape_run.ads_found} found, {scrape_run.ads_new} new, "
                f"status: {scrape_run.status}"
            )
