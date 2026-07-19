"""Kleinanzeigen-Scraper: URL-Bau, HTTP-Abruf (paginiert + Detailseiten) + Parsing."""

import logging
import re
from urllib.parse import urlencode

from app.platforms._base import PlatformScraper, SearchParams
from app.scraper import parser
from app.scraper.httpclient import fetch_page, fetch_pages
from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kleinanzeigen.de"
# Kleinanzeigen-Slugs transliterieren Umlaute (ä→ae …); Rohumlaute funktionieren zwar auch,
# aber die transliterierte Form ergibt saubere, encoding-freie URLs.
_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
# Kategorie „Zu verschenken & Tauschen" (c272), empirisch bestätigt: liefert mit
# ``?locationStr=<plz>&radiusKm=<r>`` die umkreis-gefilterten Verschenken-Anzeigen.
_GIFT_CATEGORY_PATH = "/s-zu-verschenken-tauschen/c272"


def _slugify(query: str) -> str:
    """Wandelt einen Suchbegriff in einen Kleinanzeigen-URL-Slug (lowercase, Bindestriche)."""
    text = query.strip().lower().translate(_UMLAUT_MAP)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _price_segment(min_price: float | None, max_price: float | None) -> str | None:
    """Preis-Pfadsegment 'preis:min:max' (leere Seite wenn Grenze fehlt); None ohne Preisgrenzen."""
    if min_price is None and max_price is None:
        return None
    low = "" if min_price is None else str(int(min_price))
    high = "" if max_price is None else str(int(max_price))
    return f"preis:{low}:{high}"


class KleinanzeigenScraper(PlatformScraper):
    """URL-Bau für Keyword-Suchen, paginierter Abruf + Delegation an die Parserfunktionen."""

    def build_search_url(self, params: SearchParams) -> str:
        """Baut eine Kleinanzeigen-Suchergebnis-URL aus Suchbegriff, PLZ/Radius und Preis.

        Formate empirisch bestätigt: ``/s-{slug}/k0``, Preis als Pfadsegment
        ``/s-preis:min:max/{slug}/k0``, Standort als Query ``?locationStr=&radiusKm=``.
        Im Fundgrube-Modus (``gift_only``) wird stattdessen die Verschenken-Kategorie
        im Umkreis beobachtet — ohne Suchbegriff und ohne Preisspanne.
        """
        if params.gift_only:
            return self._build_gift_url(params)

        slug = _slugify(params.query)
        if not slug:
            raise ValueError("Suchbegriff ergibt keinen gültigen URL-Slug.")

        price = _price_segment(params.min_price, params.max_price)
        path = f"/s-{price}/{slug}/k0" if price else f"/s-{slug}/k0"
        url = f"{_BASE_URL}{path}"

        query: dict[str, str | int] = {}
        if params.postal_code:
            query["locationStr"] = params.postal_code
            if params.radius_km:
                query["radiusKm"] = params.radius_km
        return f"{url}?{urlencode(query)}" if query else url

    @staticmethod
    def _build_gift_url(params: SearchParams) -> str:
        """Baut die Verschenken-Kategorie-URL im Umkreis der Nutzer-PLZ."""
        url = f"{_BASE_URL}{_GIFT_CATEGORY_PATH}"
        query: dict[str, str | int] = {}
        if params.postal_code:
            query["locationStr"] = params.postal_code
            if params.radius_km:
                query["radiusKm"] = params.radius_km
        return f"{url}?{urlencode(query)}" if query else url

    def collect_previews(self, search_url: str) -> list[ScrapedAdPreview]:
        """Lädt alle paginierten Suchergebnisseiten und sammelt Anzeigen-Vorschauen."""
        first_page_html = fetch_page(search_url)
        previews = self.parse_search_results(first_page_html)
        next_page_urls = self.parse_next_page_urls(first_page_html)

        if next_page_urls:
            for html in fetch_pages(next_page_urls):
                if html:
                    previews.extend(self.parse_search_results(html))
        return previews

    def build_details(self, previews: list[ScrapedAdPreview]) -> list[ScrapedAdDetail]:
        """Lädt für jede Vorschau die Detailseite und parst sie zu vollständigen Anzeigendaten."""
        if not previews:
            return []

        htmls = fetch_pages([p.url for p in previews])
        details: list[ScrapedAdDetail] = []
        for preview, html in zip(previews, htmls, strict=True):
            if not html:
                logger.warning(f"Failed to fetch detail page for {preview.external_id}")
                continue
            detail = self.parse_ad_detail(html, preview.url, preview.external_id)
            if detail:
                details.append(detail)
            else:
                logger.warning(f"Failed to parse detail page for {preview.external_id}")
        return details

    def parse_search_results(self, html: str) -> list[ScrapedAdPreview]:
        return parser.parse_search_results(html)

    def parse_next_page_urls(self, html: str) -> list[str]:
        return parser.parse_next_page_urls(html)

    def parse_ad_detail(self, html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
        return parser.parse_ad_detail(html, url, external_id)
