"""Tests für den Verschenken-Kategorie-URL-Bau (Fundgrube)."""

from app.platforms import get_platform
from app.platforms._base import SearchParams
from app.services.deal_analysis import is_gift_category_search_url


def _url(**kwargs) -> str:
    return get_platform("kleinanzeigen").scraper.build_search_url(SearchParams(**kwargs))


class TestGiftSearchUrl:
    def test_gift_url_with_location(self):
        url = _url(query="", postal_code="50667", radius_km=10, gift_only=True)
        assert "/s-zu-verschenken-tauschen" in url
        assert "locationStr=50667" in url
        assert "radiusKm=10" in url

    def test_gift_url_without_location(self):
        url = _url(query="", gift_only=True)
        assert url.endswith("/s-zu-verschenken-tauschen/c272")

    def test_gift_url_ignores_price_and_query(self):
        # Im Verschenken-Modus gibt es weder Preisspanne noch Suchbegriff-Slug.
        url = _url(query="fahrrad", min_price=10, max_price=50, gift_only=True)
        assert "preis:" not in url
        assert "fahrrad" not in url

    def test_gift_url_is_recognized_as_gift(self):
        assert is_gift_category_search_url(_url(query="", gift_only=True))
        assert is_gift_category_search_url(
            _url(query="", postal_code="50667", radius_km=10, gift_only=True)
        )

    def test_normal_url_is_not_gift(self):
        url = _url(query="fahrrad", postal_code="50667", radius_km=10)
        assert not is_gift_category_search_url(url)
        assert "fahrrad" in url
