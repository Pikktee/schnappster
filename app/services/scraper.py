"""Scraper-Service: fällige Suchen, Vorschau sammeln, Details holen, filtern, speichern."""

import logging
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
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
from app.services.deal_analysis import is_gift_category_search_url
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AdSearchSnapshot:
    """Detached search data so scraping does not hold a DB connection while doing HTTP."""

    id: int
    owner_id: str
    name: str
    url: str
    min_price: float | None
    max_price: float | None
    blacklist_keywords: str | None
    last_scraped_at: datetime | None
    scrape_interval_minutes: int


class ScraperService:
    """Scraping orchestrieren: fällige Suchen, Seiten holen, filtern, in der DB speichern."""

    def __init__(self, session: Session):
        """Erstellt den Service mit der übergebenen Datenbank-Session."""
        self.session = session

    def scrape_due_searches(self) -> int:
        """Scrape für alle aktiven, fälligen Suchaufträge; Zahl neu gespeicherter Anzeigen."""
        searches = [
            _snapshot_adsearch(search)
            for search in self.session.exec(
                select(AdSearch).where(col(AdSearch.is_active).is_(True))
            ).all()
            if search.id is not None
        ]
        self._release_session_connection()
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
        """True, wenn der Suchauftrag fällig ist (Intervall abgelaufen oder noch nie gescrapt)."""
        if adsearch.last_scraped_at is None:
            return True
        next_scrape = adsearch.last_scraped_at + timedelta(minutes=adsearch.scrape_interval_minutes)
        # DB kann naive Datetimes liefern; für Vergleich als UTC behandeln
        if next_scrape.tzinfo is None:
            next_scrape = next_scrape.replace(tzinfo=UTC)
        return now >= next_scrape

    def scrape_adsearch(self, adsearch: AdSearch | AdSearchSnapshot) -> ScrapeRun:
        """Scrapt alle neuen Anzeigen für einen Suchauftrag; gibt den Lauf zurück."""
        search = _snapshot_adsearch(adsearch)
        self._release_session_connection()
        started_at = datetime.now(UTC)
        ads_found_result = 0
        ads_filtered_result = 0
        ads_new_result = 0

        try:
            previews = self._collect_previews(search.url)
            new_previews = self._filter_known(previews, search.id)
            self._release_session_connection()

            logger.info(f"AdSearch '{search.name}': {len(previews)} found, {len(new_previews)} new")

            details = self._fetch_details(new_previews)
            filtered = self._filter_ads(details, search)
            ads = self._save_ads(filtered, search.id, search.owner_id)

            ads_found_result = len(previews)
            ads_filtered_result = len(details) - len(filtered)
            ads_new_result = len(ads)

        except Exception as e:
            logger.error(f"Scrape failed for '{search.name}': {e}")
            self._log_error(
                search.id,
                "ScrapeError",
                str(e),
                traceback.format_exc(),
            )
            raise

        finally:
            scrape_run = self._save_scrape_run(
                search.id,
                started_at,
                ads_found_result,
                ads_filtered_result,
                ads_new_result,
            )

        return scrape_run

    def _save_scrape_run(
        self,
        adsearch_id: int,
        started_at: datetime,
        ads_found: int,
        ads_filtered: int,
        ads_new: int,
    ) -> ScrapeRun:
        """Speichert Run-Metriken und aktualisiert den Suchauftrag in einer kurzen Transaktion."""
        finished_at = datetime.now(UTC)
        scrape_run = ScrapeRun(
            adsearch_id=adsearch_id,
            started_at=started_at,
            finished_at=finished_at,
            ads_found=ads_found,
            ads_filtered=ads_filtered,
            ads_new=ads_new,
        )
        self.session.add(scrape_run)
        if adsearch := self.session.get(AdSearch, adsearch_id):
            adsearch.last_scraped_at = finished_at
        self.session.commit()
        return scrape_run

    def _release_session_connection(self) -> None:
        """Beendet reine Read-Transaktionen vor langen externen Netzwerkaufrufen."""
        try:
            self.session.rollback()
        except SQLAlchemyError:
            self.session.invalidate()
        finally:
            self.session.close()

    def _log_error(
        self,
        adsearch_id: int | None,
        error_type: str,
        message: str,
        details: str | None = None,
    ) -> None:
        """Schreibt einen Fehler in die Tabelle error_logs."""
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
        self, details: list[ScrapedAdDetail], adsearch: AdSearchSnapshot
    ) -> list[ScrapedAdDetail]:
        """Filtert Details nach Suchauftrag und globalen Einstellungen (Preis, Blacklist, …)."""
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
        adsearch: AdSearch | AdSearchSnapshot,
        exclude_commercial: bool,
        min_rating: int,
    ) -> str | None:
        """Kurzer Grund-String, wenn die Anzeige aussortiert werden soll, sonst None."""
        # Nur Anzeigen mit ausschließlich VB (ohne angegebenen Preis) aussortieren.
        # "VB + Preis" (z.B. "1.999 € VB") soll gespeichert werden; nur reines VB nicht.
        is_vb = (detail.price_type == "NEGOTIABLE") or ("vb" in (detail.price_raw or "").lower())
        if is_vb and detail.price is None:
            return "VB-Anzeige (Preis Verhandlungsbasis) ohne angegebenen Preis"

        # Zu-verschenken-Kategorie: Anzeigen aus "Verschenken & Tauschen" immer behalten,
        # auch ohne numerischen Preis. Die Suchauftrag-URL zählt als Fallback, falls die
        # Detailseite die Kategorie-Metadaten nicht mehr sauber liefert.
        is_giveaway_category = any(
            name and name.lower().startswith("zu_verschenken")
            for name in (detail.category_l1, detail.category_l2)
        )
        is_giveaway_search = is_gift_category_search_url(adsearch.url)
        if detail.price is None and (is_giveaway_category or is_giveaway_search):
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
        """Lädt alle paginierten Suchergebnisseiten und sammelt Anzeigen-Vorschauen."""
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
        """Entfernt Vorschauen, deren external_id für diesen Suchauftrag bereits existiert."""
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
        """Lädt die Detailseiten für jede Vorschau und parst sie in eine ScrapedAdDetail-Liste."""
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

    def _save_ads(
        self, details: list[ScrapedAdDetail], adsearch_id: int, owner_id: str
    ) -> list[Ad]:
        """Speichert gescrapte Details in ``ads`` und gibt die neuen ``Ad``-Instanzen zurück."""
        ads: list[Ad] = []

        for detail in details:
            ad = Ad(
                owner_id=owner_id,
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


def _snapshot_adsearch(adsearch: AdSearch | AdSearchSnapshot) -> AdSearchSnapshot:
    """Kopiert nur die Werte, die der Scraper braucht; keine lazy DB-Verbindung danach."""
    if isinstance(adsearch, AdSearchSnapshot):
        return adsearch
    if adsearch.id is None:
        raise ValueError("AdSearch muss eine ID haben, um gescrapt zu werden")
    return AdSearchSnapshot(
        id=adsearch.id,
        owner_id=adsearch.owner_id,
        name=adsearch.name,
        url=adsearch.url,
        min_price=adsearch.min_price,
        max_price=adsearch.max_price,
        blacklist_keywords=adsearch.blacklist_keywords,
        last_scraped_at=adsearch.last_scraped_at,
        scrape_interval_minutes=adsearch.scrape_interval_minutes,
    )
