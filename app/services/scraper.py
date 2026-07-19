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
from app.platforms import DEFAULT_PLATFORM, get_platform
from app.scraper.parser import ScrapedAdDetail
from app.services.deal_analysis import is_gift_category_search_url
from app.services.geo import postal_distance_km
from app.services.relevance import title_matches_query
from app.services.settings import SettingsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AdSearchSnapshot:
    """Detached search data so scraping does not hold a DB connection while doing HTTP."""

    id: int
    owner_id: str
    name: str
    url: str
    platform: str
    search_query: str | None
    postal_code: str | None
    min_price: float | None
    max_price: float | None
    blacklist_keywords: str | None
    blacklist_categories: str | None
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

        scraper = get_platform(search.platform).scraper
        try:
            previews = scraper.collect_previews(search.url)
            new_previews = self._filter_known(previews, search.id)
            self._release_session_connection()

            logger.info(f"AdSearch '{search.name}': {len(previews)} found, {len(new_previews)} new")

            details = scraper.build_details(new_previews)
            filtered = self._filter_ads(details, search)
            ads = self._save_ads(filtered, search)

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
        # Relevanz: eBay/MyDealz füllen die Trefferliste bei seltenen Begriffen mit lose
        # passenden Angeboten auf. Nur behalten, wenn alle Suchbegriff-Tokens im Titel stehen
        # (ohne Suchbegriff, d.h. rein URL-basierte Suche, wird nicht gefiltert).
        if not title_matches_query(detail.title, adsearch.search_query):
            return f"Titel passt nicht zum Suchbegriff '{adsearch.search_query}'"

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

        # Ausgeschlossene Kategorien (Fundgrube). Kleinanzeigen liefert category_l2 aktuell
        # oft nicht mehr → best effort; die semantische Junk-Filterung trägt die Nano-Stufe.
        if adsearch.blacklist_categories and detail.category_l2:
            excluded = {
                c.strip().lower() for c in adsearch.blacklist_categories.split(",") if c.strip()
            }
            if detail.category_l2.lower() in excluded:
                return f"Ausgeschlossene Kategorie '{detail.category_l2}'"

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

    def _save_ads(
        self, details: list[ScrapedAdDetail], search: AdSearchSnapshot
    ) -> list[Ad]:
        """Speichert gescrapte Details in ``ads`` und gibt die neuen ``Ad``-Instanzen zurück.

        Berechnet die Luftlinie zur Nutzer-PLZ (falls beide vorhanden) für die Fundgrube-
        Aufwand-Achse; bei normalen Suchen ohne PLZ bleibt ``distance_km`` None.
        """
        ads: list[Ad] = []

        for detail in details:
            distance_km = None
            if search.postal_code and detail.postal_code:
                distance_km = postal_distance_km(search.postal_code, detail.postal_code)
            ad = Ad(
                owner_id=search.owner_id,
                external_id=detail.external_id,
                title=detail.title,
                url=detail.url,
                description=detail.description,
                price=detail.price,
                postal_code=detail.postal_code,
                city=detail.city,
                distance_km=distance_km,
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
                adsearch_id=search.id,
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
        platform=adsearch.platform or DEFAULT_PLATFORM,
        search_query=adsearch.search_query,
        postal_code=adsearch.postal_code,
        min_price=adsearch.min_price,
        max_price=adsearch.max_price,
        blacklist_keywords=adsearch.blacklist_keywords,
        blacklist_categories=adsearch.blacklist_categories,
        last_scraped_at=adsearch.last_scraped_at,
        scrape_interval_minutes=adsearch.scrape_interval_minutes,
    )
