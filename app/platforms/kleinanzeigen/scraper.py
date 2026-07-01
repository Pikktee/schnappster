"""Kleinanzeigen-Scraper: URL-Bau + dünner Adapter auf app.scraper.parser."""

import re
from urllib.parse import urlencode

from app.platforms._base import PlatformScraper, SearchParams
from app.scraper import parser
from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview

_BASE_URL = "https://www.kleinanzeigen.de"
# Kleinanzeigen-Slugs transliterieren Umlaute (ä→ae …); Rohumlaute funktionieren zwar auch,
# aber die transliterierte Form ergibt saubere, encoding-freie URLs.
_UMLAUT_MAP = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


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
    """URL-Bau für Keyword-Suchen + Delegation an die Kleinanzeigen-Parserfunktionen."""

    def build_search_url(self, params: SearchParams) -> str:
        """Baut eine Kleinanzeigen-Suchergebnis-URL aus Suchbegriff, PLZ/Radius und Preis.

        Formate empirisch bestätigt: ``/s-{slug}/k0``, Preis als Pfadsegment
        ``/s-preis:min:max/{slug}/k0``, Standort als Query ``?locationStr=&radiusKm=``.
        """
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

    def parse_search_results(self, html: str) -> list[ScrapedAdPreview]:
        return parser.parse_search_results(html)

    def parse_next_page_urls(self, html: str) -> list[str]:
        return parser.parse_next_page_urls(html)

    def parse_ad_detail(self, html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
        return parser.parse_ad_detail(html, url, external_id)
