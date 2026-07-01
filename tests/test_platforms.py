"""Tests für die Plattform-Registry und den Kleinanzeigen-Scraper-Adapter."""

import pytest

from app.platforms import (
    DEFAULT_PLATFORM,
    SearchParams,
    get_all_platform_names,
    get_platform,
)
from app.platforms._base import PlatformDefinition, PlatformScraper
from app.platforms.kleinanzeigen import Kleinanzeigen
from app.scraper import parser

_KA = "https://www.kleinanzeigen.de"


def test_registry_contains_kleinanzeigen():
    """Kleinanzeigen ist registriert und über den Namen auflösbar."""
    assert "kleinanzeigen" in get_all_platform_names()
    assert isinstance(get_platform("kleinanzeigen"), Kleinanzeigen)


def test_get_platform_falls_back_to_default_for_unknown():
    """Unbekannte Namen liefern die Standard-Plattform statt eines KeyError."""
    assert get_platform("gibt-es-nicht").name == DEFAULT_PLATFORM


def test_kleinanzeigen_scraper_is_a_platform_scraper():
    """Der Kleinanzeigen-Scraper erfüllt das PlatformScraper-Interface."""
    assert isinstance(get_platform("kleinanzeigen").scraper, PlatformScraper)


def test_kleinanzeigen_scraper_delegates_to_parser():
    """Der Adapter liefert dieselben Ergebnisse wie die Parser-Modulfunktionen."""
    scraper = get_platform("kleinanzeigen").scraper
    html = "<html><body><ul></ul></body></html>"
    assert scraper.parse_search_results(html) == parser.parse_search_results(html)
    assert scraper.parse_next_page_urls(html) == parser.parse_next_page_urls(html)
    assert scraper.parse_ad_detail(html, "https://example.com/x", "1") is None


def test_platform_definition_requires_name_and_scraper():
    """Eine unvollständige Plattform-Definition schlägt schon bei der Klassendefinition fehl."""
    with pytest.raises(TypeError):

        class Broken(PlatformDefinition):  # fehlt: name, scraper
            pass


# --- build_search_url (Format empirisch gegen kleinanzeigen.de bestätigt) ---


def test_build_search_url_keyword_only():
    """Reiner Suchbegriff: lowercase, Leerzeichen werden zu Bindestrichen."""
    scraper = get_platform("kleinanzeigen").scraper
    url = scraper.build_search_url(SearchParams(query="iPhone 15 Pro"))
    assert url == f"{_KA}/s-iphone-15-pro/k0"


def test_build_search_url_transliterates_umlauts():
    """Umlaute werden transliteriert (ä→ae, ö→oe, ü→ue, ß→ss)."""
    scraper = get_platform("kleinanzeigen").scraper
    assert scraper.build_search_url(SearchParams(query="Bürostuhl")) == f"{_KA}/s-buerostuhl/k0"


def test_build_search_url_with_location():
    """PLZ + Radius landen als Query-Parameter locationStr/radiusKm."""
    scraper = get_platform("kleinanzeigen").scraper
    url = scraper.build_search_url(SearchParams(query="iphone", postal_code="50667", radius_km=50))
    assert url == f"{_KA}/s-iphone/k0?locationStr=50667&radiusKm=50"


def test_build_search_url_with_price_segment():
    """Preisgrenzen werden zum Pfadsegment preis:min:max."""
    scraper = get_platform("kleinanzeigen").scraper
    url = scraper.build_search_url(SearchParams(query="iphone", min_price=100, max_price=500))
    assert url == f"{_KA}/s-preis:100:500/iphone/k0"


def test_build_search_url_rejects_empty_slug():
    """Ein Suchbegriff ohne verwertbare Zeichen ist ein Fehler."""
    scraper = get_platform("kleinanzeigen").scraper
    with pytest.raises(ValueError, match="Slug"):
        scraper.build_search_url(SearchParams(query="!!!"))
