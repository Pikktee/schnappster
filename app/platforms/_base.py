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
    # Fundgrube: gesamte „Zu verschenken"-Kategorie im Umkreis statt Keyword-Suche.
    gift_only: bool = False


class PlatformScraper(ABC):
    """Scraping-Logik einer Plattform: URL-Bau, HTTP-Abruf und HTML-Parsing.

    Die Plattform besitzt ihren **HTTP-Abruf** selbst (Kleinanzeigen: direkter curl-cffi-Client;
    eBay: Session + Proxy-Fallback), weil sich Fingerprinting, Cookies und Proxy je Quelle
    unterscheiden. Der ``ScraperService`` orchestriert nur (bekannte aussortieren, filtern,
    speichern) und kennt keine plattformspezifischen Fetch-Details.
    """

    @abstractmethod
    def build_search_url(self, params: SearchParams) -> str:
        """Baut die Suchergebnis-URL aus plattformunabhängigen Suchparametern."""

    @abstractmethod
    def collect_previews(self, search_url: str) -> list[ScrapedAdPreview]:
        """Holt die Suchergebnisseite(n) inkl. Paginierung und parst Anzeigen-Vorschauen."""

    @abstractmethod
    def build_details(self, previews: list[ScrapedAdPreview]) -> list[ScrapedAdDetail]:
        """Ergänzt Vorschauen zu vollständigen Anzeigendaten.

        Kleinanzeigen holt dafür je Vorschau die Detailseite; eBay hat bereits alle Daten in der
        Trefferkarte und mappt sie ohne weiteren Abruf.
        """


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
