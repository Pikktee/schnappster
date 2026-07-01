"""Plattform-Abstraktion: jede Quelle (Kleinanzeigen; künftig eBay, MyDealz) als Plugin.

``ScraperService`` und weitere Konsumenten arbeiten nur gegen diese Interfaces, nie gegen
konkrete Plattformen. Neue Quelle = neues Package unter ``app/platforms/`` + Registry-Eintrag.

Diese erste Ausbaustufe kapselt nur das HTML-Parsing. Der keyword-basierte URL-Bau
(``build_search_url``) und Plattform-Capabilities folgen mit der keyword-basierten Suche,
wo sie gegen die echten Seiten validiert werden können.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from app.scraper.parser import ScrapedAdDetail, ScrapedAdPreview


@dataclass(frozen=True, slots=True)
class SearchParams:
    """Plattformunabhängige Suchparameter für den keyword-basierten URL-Bau."""

    query: str
    postal_code: str | None = None
    radius_km: int | None = None
    min_price: float | None = None
    max_price: float | None = None


class PlatformScraper(ABC):
    """Reine Scraping-Logik einer Plattform: HTML-Parsing, kein DB- oder Business-Code."""

    @abstractmethod
    def build_search_url(self, params: SearchParams) -> str:
        """Baut die Suchergebnis-URL aus plattformunabhängigen Suchparametern."""

    @abstractmethod
    def parse_search_results(self, html: str) -> list[ScrapedAdPreview]:
        """Parst Anzeigen-Vorschauen aus dem HTML einer Suchergebnisseite."""

    @abstractmethod
    def parse_next_page_urls(self, html: str) -> list[str]:
        """Extrahiert die Paginierungs-URLs aus einer Suchergebnisseite."""

    @abstractmethod
    def parse_ad_detail(self, html: str, url: str, external_id: str) -> ScrapedAdDetail | None:
        """Parst eine Detailseite zu vollständigen Anzeigendaten; None wenn ungültig."""


class PlatformDefinition:
    """Bündelt Name und Scraper einer Plattform.

    ``__init_subclass__`` erzwingt beim Import, dass Unterklassen die Pflichtattribute setzen –
    so schlägt eine unvollständige Plattform sofort und nicht erst zur Laufzeit fehl.
    """

    name: ClassVar[str]
    scraper: ClassVar[PlatformScraper]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("name", "scraper"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} muss '{attr}' als Klassenattribut definieren")
