"""Manual scraper invocation via command line.

Usage:
    uv run python -m app.scraper.run           # scrape all active AdSearches
    uv run python -m app.scraper.run 1         # scrape AdSearch with ID 1
"""

import logging
import sys

from sqlmodel import Session, select

from app.core.db import engine
from app.models.adsearch import AdSearch
from app.scraper.service import ScraperService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    adsearch_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with Session(engine) as session:
        if adsearch_id:
            adsearch = session.get(AdSearch, adsearch_id)
            if not adsearch:
                logger.error(f"AdSearch with ID {adsearch_id} not found")
                sys.exit(1)
            searches = [adsearch]
        else:
            searches = list(
                session.exec(select(AdSearch).where(AdSearch.is_active.is_(True))).all()
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


if __name__ == "__main__":
    main()
