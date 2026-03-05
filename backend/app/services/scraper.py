import logging
from datetime import datetime

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
from app.services.settings import get_setting_bool, get_setting_int

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
            filtered = self._filter_ads(details, adsearch)
            ads = self._save_ads(filtered, adsearch.id)

            scrape_run.ads_found = len(previews)
            scrape_run.ads_new = len(ads)
            scrape_run.status = "completed"

        except Exception as e:
            logger.error(f"Scrape failed for '{adsearch.name}': {e}")
            scrape_run.status = "failed"
            raise

        finally:
            scrape_run.finished_at = datetime.utcnow()
            adsearch.last_scraped_at = datetime.utcnow()
            self.session.commit()

        return scrape_run

    def _filter_ads(
        self, details: list[ScrapedAdDetail], adsearch: AdSearch
    ) -> list[ScrapedAdDetail]:
        """Filter ads based on AdSearch and global settings."""
        exclude_commercial = get_setting_bool("exclude_commercial_sellers", self.session)
        min_rating = get_setting_int("min_seller_rating", self.session)

        filtered = []
        for detail in details:
            reason = self._get_filter_reason(detail, adsearch, exclude_commercial, min_rating)
            if reason:
                logger.info(f"Filtered out '{detail.title}': {reason}")
            else:
                filtered.append(detail)

        if len(details) != len(filtered):
            logger.info(f"Filtered {len(details) - len(filtered)} of {len(details)} ads")

        return filtered

    @staticmethod
    def _get_filter_reason(
        detail: ScrapedAdDetail,
        adsearch: AdSearch,
        exclude_commercial: bool,
        min_rating: int,
    ) -> str | None:
        """Return filter reason or None if ad passes all filters."""
        # Preisfilter (pro Suche)
        if detail.price is not None:
            if adsearch.min_price is not None and detail.price < adsearch.min_price:
                return f"Preis {detail.price}€ unter Minimum {adsearch.min_price}€"
            if adsearch.max_price is not None and detail.price > adsearch.max_price:
                return f"Preis {detail.price}€ über Maximum {adsearch.max_price}€"

        # Blacklist (pro Suche)
        if adsearch.blacklist_keywords:
            keywords = [k.strip().lower() for k in adsearch.blacklist_keywords.split(",")]
            title_lower = detail.title.lower()
            desc_lower = (detail.description or "").lower()
            for keyword in keywords:
                if keyword and (keyword in title_lower or keyword in desc_lower):
                    return f"Blacklist-Keyword '{keyword}'"

        # Gewerbliche Verkäufer (global)
        if exclude_commercial and detail.seller_type and detail.seller_type.lower() == "gewerblich":
            return "Gewerblicher Verkäufer"

        # Mindest-Rating (global)
        if detail.seller_rating is not None and detail.seller_rating < min_rating:
            rating_labels = {2: "TOP", 1: "OK", 0: "Na ja"}
            return (
                f"Verkäufer-Rating '{rating_labels.get(detail.seller_rating, '?')}' "
                f"unter Minimum '{rating_labels.get(min_rating, '?')}'"
            )

        return None

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
