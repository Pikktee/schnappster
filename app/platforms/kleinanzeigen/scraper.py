"""Kleinanzeigen-Scraper: dünner Adapter auf die bestehende Parselogik in app.scraper.parser."""

from app.platforms._base import PlatformScraper
from app.scraper import parser
from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview


class KleinanzeigenScraper(PlatformScraper):
    """Delegiert an die unveränderten Kleinanzeigen-Parserfunktionen."""

    def parse_search_results(self, html: str) -> list[ScrapedAdPreview]:
        return parser.parse_search_results(html)

    def parse_next_page_urls(self, html: str) -> list[str]:
        return parser.parse_next_page_urls(html)

    def parse_ad_detail(self, html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
        return parser.parse_ad_detail(html, url, external_id)
