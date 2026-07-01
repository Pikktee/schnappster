"""Kleinanzeigen.de als Plattform-Definition – die bislang einzige Quelle."""

from app.platforms._base import PlatformDefinition
from app.platforms.kleinanzeigen.scraper import KleinanzeigenScraper


class Kleinanzeigen(PlatformDefinition):
    """Kleinanzeigen.de (Privatverkauf)."""

    name = "kleinanzeigen"
    scraper = KleinanzeigenScraper()
