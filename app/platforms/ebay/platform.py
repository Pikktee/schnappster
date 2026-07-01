"""eBay.de als Plattform-Definition (Kaufquelle für aktive Angebote)."""

from app.platforms._base import PlatformDefinition
from app.platforms.ebay.scraper import EbayScraper


class Ebay(PlatformDefinition):
    """eBay.de (aktive Angebote, bundesweiter Versand)."""

    name = "ebay"
    scraper = EbayScraper()
