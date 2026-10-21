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


def test_registry_contains_ebay():
    """eBay ist als zweite Quelle registriert und erfüllt das PlatformScraper-Interface."""
    assert "ebay" in get_all_platform_names()
    assert isinstance(get_platform("ebay").scraper, PlatformScraper)


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


# --- Orts-ID im Pfad (Kleinanzeigen seit 2026) ---


@pytest.fixture
def fake_location_ids(monkeypatch):
    """Orts-ID-Auflösung ohne Netz: 60311 → 18709, sonst unbekannt."""
    from app.platforms.kleinanzeigen import scraper as ka_scraper

    monkeypatch.setattr(
        ka_scraper, "resolve_location_id", lambda plz: 18709 if plz == "60311" else None
    )
    return ka_scraper


def test_localize_search_url_keyword_with_price(fake_location_ids):
    """Keyword-Suche mit Preis: PLZ vorn, Orts-ID und Umkreis am Ende."""
    url = f"{_KA}/s-preis:300:1500/rennrad-carbon/k0?locationStr=60311&radiusKm=30"
    assert (
        fake_location_ids.localize_search_url(url)
        == f"{_KA}/s-60311/preis:300:1500/rennrad-carbon/k0l18709r30"
    )


def test_localize_search_url_keyword_without_radius(fake_location_ids):
    """Ohne Umkreis nur die Orts-ID."""
    url = f"{_KA}/s-siebtraeger/k0?locationStr=60311"
    assert fake_location_ids.localize_search_url(url) == f"{_KA}/s-60311/siebtraeger/k0l18709"


def test_localize_search_url_gift_category(fake_location_ids):
    """Verschenken-Kategorie: Kategorie-Slug vorn, dann PLZ, dann c272 mit Orts-ID."""
    url = f"{_KA}/s-zu-verschenken-tauschen/c272?locationStr=60311&radiusKm=10"
    assert (
        fake_location_ids.localize_search_url(url)
        == f"{_KA}/s-zu-verschenken-tauschen/60311/c272l18709r10"
    )


def test_localize_search_url_leaves_other_urls_alone(fake_location_ids):
    """Ohne Ort, mit unbekannter PLZ oder bei fertigen Pfad-URLs bleibt alles, wie es ist."""
    plain = f"{_KA}/s-iphone/k0"
    unknown = f"{_KA}/s-iphone/k0?locationStr=99999&radiusKm=5"
    native = f"{_KA}/s-audio-hifi/60325/podmic/k0c172l4305r250"
    for url in (plain, unknown, native):
        assert fake_location_ids.localize_search_url(url) == url


def test_resolve_location_id_parses_suggestions(monkeypatch):
    """Erster Vorschlag mit passender PLZ gewinnt; 'Deutschland' (_0) wird übersprungen."""
    from app.platforms.kleinanzeigen import scraper as ka_scraper

    monkeypatch.setattr(ka_scraper, "_location_ids", {})
    monkeypatch.setattr(
        ka_scraper,
        "fetch_page_with_status",
        lambda url: (
            200,
            '{"_0":"Deutschland","_18709":"60311 Altstadt","_4296":"60311 Innenstadt"}',
        ),
    )
    assert ka_scraper.resolve_location_id("60311") == 18709
