import logging

from sqlmodel import Session, select

from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.scraperun import ScrapeRun
from app.scraper.httpclient import fetch_page, fetch_pages
from app.scraper.parser import (
    ScrapedAdDetail,
    parse_ad_detail,
    parse_next_page_urls,
    parse_search_results,
)

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self, session: Session):
        self.session = session

    def scrape_adsearch(self, adsearch: AdSearch) -> ScrapeRun:
        """Scrape all new ads for a given AdSearch."""
        scrape_run = ScrapeRun(adsearch_id=adsearch.id, status="running")
        self.session.add(scrape_run)
        self.session.commit()

        try:
            previews = self._collect_previews(adsearch.url)
            new_previews = self._filter_known(previews, adsearch.id)

            logger.info(
                f"AdSearch '{adsearch.name}': {len(previews)} found, {len(new_previews)} new"
            )

            details = self._fetch_details(new_previews)
            ads = self._save_ads(details, adsearch.id)

            scrape_run.ads_found = len(previews)
            scrape_run.ads_new = len(ads)
            scrape_run.status = "completed"

        except Exception as e:
            logger.error(f"Scrape failed for '{adsearch.name}': {e}")
            scrape_run.status = "failed"
            raise

        finally:
            from datetime import datetime

            scrape_run.finished_at = datetime.utcnow()
            adsearch.last_scraped_at = datetime.utcnow()
            self.session.commit()

        return scrape_run

    def _collect_previews(self, search_url: str) -> list:
        """Fetch all pages of search results and collect ad previews."""
        first_page_html = fetch_page(search_url)
        all_previews = parse_search_results(first_page_html)
        next_page_urls = parse_next_page_urls(first_page_html)

        if next_page_urls:
            page_htmls = fetch_pages(next_page_urls)
            for html in page_htmls:
                if html:
                    all_previews.extend(parse_search_results(html))

        return all_previews

    def _filter_known(self, previews: list, adsearch_id: int) -> list:
        """Filter out ads that already exist in the database."""
        if not previews:
            return []

        external_ids = [p.external_id for p in previews]
        existing = self.session.exec(
            select(Ad.external_id).where(
                Ad.external_id.in_(external_ids),
                Ad.adsearch_id == adsearch_id,
            )
        ).all()
        existing_ids = set(existing)

        return [p for p in previews if p.external_id not in existing_ids]

    def _fetch_details(self, previews: list) -> list[ScrapedAdDetail]:
        """Fetch detail pages for all new ads."""
        if not previews:
            return []

        urls = [p.url for p in previews]
        htmls = fetch_pages(urls)

        details: list[ScrapedAdDetail] = []
        for preview, html in zip(previews, htmls, strict=True):
            if not html:
                logger.warning(f"Failed to fetch detail page for {preview.external_id}")
                continue
            detail = parse_ad_detail(html, preview.url, preview.external_id)
            if detail:
                details.append(detail)
            else:
                logger.warning(f"Failed to parse detail page for {preview.external_id}")

        return details

    def _save_ads(self, details: list[ScrapedAdDetail], adsearch_id: int) -> list[Ad]:
        """Save scraped ad details to database."""
        ads: list[Ad] = []

        for detail in details:
            ad = Ad(
                external_id=detail.external_id,
                title=detail.title,
                url=detail.url,
                description=detail.description,
                price=detail.price,
                postal_code=detail.postal_code,
                city=detail.city,
                condition=detail.condition,
                shipping_cost=detail.shipping_cost,
                image_urls=",".join(detail.image_urls),
                seller_name=detail.seller_name,
                seller_url=detail.seller_url,
                seller_rating=detail.seller_rating,
                seller_is_friendly=detail.seller_is_friendly,
                seller_is_reliable=detail.seller_is_reliable,
                seller_type=detail.seller_type,
                seller_active_since=detail.seller_active_since,
                adsearch_id=adsearch_id,
            )
            self.session.add(ad)
            ads.append(ad)

        self.session.commit()
        return ads
