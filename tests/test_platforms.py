"""Tests für die Plattform-Registry und den Kleinanzeigen-Scraper-Adapter."""

import pytest

from app.platforms import (
    DEFAULT_PLATFORM,
    get_all_platform_names,
    get_platform,
)
from app.platforms._base import PlatformDefinition, PlatformScraper
from app.platforms.kleinanzeigen import Kleinanzeigen
from app.scraper import parser


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
