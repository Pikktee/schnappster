"""eBay-Scraper: URL-Bau + Trefferlisten-Abruf (Session/Proxy), ohne Detailseiten.

eBay ist eine **Kaufquelle**: die aktive Trefferliste enthält bereits alle Anzeigendaten, daher
mappt ``build_details`` die Vorschauen ohne weiteren Abruf. Standort (PLZ/Radius) wird ignoriert —
eBay-Angebote werden bundesweit versendet.
"""

import logging

from app.platforms._base import PlatformScraper, SearchParams
from app.scraper import ebay_active
from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview

logger = logging.getLogger(__name__)


class EbayScraper(PlatformScraper):
    """eBay.de (aktive Angebote): Keyword-Suche, Trefferkarten-Parsing ohne Detailseiten."""

    def build_search_url(self, params: SearchParams) -> str:
        """Baut die eBay-Aktiv-Such-URL aus Suchbegriff und Preisgrenzen (Standort entfällt)."""
        query = params.query.strip()
        if not query:
            raise ValueError("Suchbegriff darf für die eBay-Suche nicht leer sein.")
        return ebay_active.build_active_search_url(query, params.min_price, params.max_price)

    def collect_previews(self, search_url: str) -> list[ScrapedAdPreview]:
        """Holt die eBay-Trefferliste (Seite 1, neu zuerst) und parst die Anzeigen-Vorschauen.

        Bei Blockade (aus dem Rechenzentrum ohne Proxy) leere Liste + Warnung statt Exception —
        so bleibt der Scrape-Lauf sauber und andere Quellen laufen weiter.
        """
        status, html = ebay_active.fetch_active_html(search_url)
        if not ebay_active.is_usable(status, html):
            logger.warning("eBay-Trefferliste nicht abrufbar (HTTP %s) für %s", status, search_url)
            return []
        return ebay_active.parse_active_listings(html)

    def build_details(self, previews: list[ScrapedAdPreview]) -> list[ScrapedAdDetail]:
        """Mappt die bereits vollständigen Trefferkarten-Daten ohne weiteren Abruf zu Details."""
        return [
            ScrapedAdDetail(
                external_id=preview.external_id,
                title=preview.title,
                url=preview.url,
                price=preview.price,
                price_raw=preview.price_raw,
                condition=preview.condition,
                shipping_cost=preview.shipping_cost,
                seller_type=preview.seller_type,
                image_urls=[preview.image_url] if preview.image_url else [],
            )
            for preview in previews
        ]
