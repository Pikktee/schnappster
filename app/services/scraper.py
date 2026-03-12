"""Scraper service: due searches, collect previews, fetch details, filter, save."""

import logging
import traceback
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.scraper.httpclient import fetch_page, fetch_pages
from app.scraper.parser import (
    ScrapedAdDetail,
    parse_ad_detail,
    parse_next_page_urls,
    parse_search_results,
)
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)


class ScraperService:
    """Orchestrates scraping: load due AdSearches, fetch pages, filter ads, persist to DB."""

    def __init__(self, session: Session):
        """Create service with the given database session."""
        self.session = session

    def scrape_due_searches(self) -> int:
        """Run scrape for all active AdSearches that are due; return total new ads saved."""
        searches = self.session.exec(
            select(AdSearch).where(col(AdSearch.is_active).is_(True))
        ).all()
        logger.info(f"Found {len(searches)} active AdSearches")

        total_new = 0
        now = datetime.now(UTC)
        for adsearch in searches:
            if not self._is_due(adsearch, now):
                continue
            try:
                scrape_run = self.scrape_adsearch(adsearch)
                total_new += scrape_run.ads_new or 0
            except Exception as e:
                logger.error(f"Failed '{adsearch.name}': {e}")
                self._log_error(
                    adsearch.id,
                    "ScrapeError",
                    str(e),
                    traceback.format_exc(),
                )
        return total_new

    @staticmethod
    def _is_due(adsearch: AdSearch, now: datetime) -> bool:
        """Return True if the AdSearch is due for scraping (interval elapsed or never scraped)."""
        if adsearch.last_scraped_at is None:
            return True
        next_scrape = adsearch.last_scraped_at + timedelta(minutes=adsearch.scrape_interval_minutes)
        # DB may return naive datetimes; treat as UTC for comparison
        if next_scrape.tzinfo is None:
            next_scrape = next_scrape.replace(tzinfo=UTC)
        return now >= next_scrape

    def scrape_adsearch(self, adsearch: AdSearch) -> ScrapeRun:
        """Scrape all new ads for one AdSearch; return run."""
        assert adsearch.id is not None, "AdSearch muss eine ID haben, um gescrapt zu werden"
        started_at = datetime.now(UTC)
        ads_found_result = 0
        ads_filtered_result = 0
        ads_new_result = 0

        try:
            previews = self._collect_previews(adsearch.url)
            new_previews = self._filter_known(previews, adsearch.id)

            logger.info(
                f"AdSearch '{adsearch.name}': {len(previews)} found, {len(new_previews)} new"
            )

            details = self._fetch_details(new_previews)
            filtered = self._filter_ads(details, adsearch)
            ads = self._save_ads(filtered, adsearch.id)

            ads_found_result = len(previews)
            ads_filtered_result = len(details) - len(filtered)
            ads_new_result = len(ads)

        except Exception as e:
            logger.error(f"Scrape failed for '{adsearch.name}': {e}")
            self._log_error(
                adsearch.id,
                "ScrapeError",
                str(e),
                traceback.format_exc(),
            )
            raise

        finally:
            finished_at = datetime.now(UTC)
            scrape_run = ScrapeRun(
                adsearch_id=adsearch.id,
                started_at=started_at,
                finished_at=finished_at,
                ads_found=ads_found_result,
                 ads_filtered=ads_filtered_result,
                ads_new=ads_new_result,
            )
            self.session.add(scrape_run)
            adsearch.last_scraped_at = finished_at
            self.session.commit()

        return scrape_run

    def _log_error(
        self,
        adsearch_id: int | None,
        error_type: str,
        message: str,
        details: str | None = None,
    ) -> None:
        """Persist an error to the error_logs table."""
        self.session.add(
            ErrorLog(
                adsearch_id=adsearch_id,
                error_type=error_type,
                message=message,
                details=details or None,
            )
        )
        self.session.commit()

    def _filter_ads(
        self, details: list[ScrapedAdDetail], adsearch: AdSearch
    ) -> list[ScrapedAdDetail]:
        """Filter details by AdSearch and global settings (price, blacklist, seller, rating)."""
        settings = SettingsService(self.session)
        exclude_commercial = settings.get_bool("exclude_commercial_sellers")
        min_rating = settings.get_int("min_seller_rating")

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
        """Return a short reason string if ad should be filtered out, else None."""
        # Nur Anzeigen mit ausschließlich VB (ohne angegebenen Preis) aussortieren.
        # "VB + Preis" (z.B. "1.999 € VB") soll gespeichert werden; nur reines VB nicht.
        is_vb = (detail.price_type == "NEGOTIABLE") or (
            "vb" in (detail.price_raw or "").lower()
        )
        if is_vb and detail.price is None:
            return "VB-Anzeige (Preis Verhandlungsbasis) ohne angegebenen Preis"

        # Zu-verschenken-Kategorie: Anzeigen aus "Verschenken & Tauschen" immer behalten,
        # auch ohne numerischen Preis.
        is_giveaway_category = any(
            name and name.lower().startswith("zu_verschenken")
            for name in (detail.category_l1, detail.category_l2)
        )
        if detail.price is None and is_giveaway_category:
            pass  # nicht filtern
        elif detail.price is None:
            return "Kein Preis angegeben (weder Betrag noch 'Zu verschenken'-Kategorie)"

        # Preisfilter pro Suchauftrag (nur bei numerischem Preis)
        if detail.price is not None:
            if adsearch.min_price is not None and detail.price < adsearch.min_price:
                return f"Preis {detail.price}€ unter Minimum {adsearch.min_price}€"
            if adsearch.max_price is not None and detail.price > adsearch.max_price:
                return f"Preis {detail.price}€ über Maximum {adsearch.max_price}€"

        # Blacklist (per search)
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
        """Fetch all paginated search result pages and collect ad previews."""
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
        """Drop previews whose external_id already exists for this adsearch_id."""
        if not previews:
            return []

        external_ids = [p.external_id for p in previews]
        existing = self.session.exec(
            select(Ad.external_id).where(
                col(Ad.external_id).in_(external_ids),
                Ad.adsearch_id == adsearch_id,
            )
        ).all()
        existing_ids = set(existing)

        return [p for p in previews if p.external_id not in existing_ids]

    def _fetch_details(self, previews: list) -> list[ScrapedAdDetail]:
        """Fetch detail pages for each preview and parse into ScrapedAdDetail list."""
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
        """Insert scraped ad details into the ads table and return created Ad instances."""
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
