"""Tests für die eBay-Kaufquelle: Trefferlisten-Parser, URL-Bau, Fetch-Fallback, Scraper."""

from unittest.mock import patch

import pytest

from app.platforms import SearchParams, get_platform
from app.scraper import ebay_active

# HTML, das die verifizierte eBay-Aktiv-Struktur nachbildet (inkl. Platzhalterkarte ohne Item-Link).
_ACTIVE_HTML = """
<ul>
  <li class="s-card">
    <div class="s-card__title">Shop on eBay</div>
    <div class="s-card__price">EUR 20,00</div>
  </li>
  <li class="s-card">
    <a href="https://www.ebay.de/itm/123456789012?_trk=abc&amp;hash=x">Zum Angebot</a>
    <div class="s-card__title">Sony WH-1000XM5 Schwarz Wird in neuem Fenster oder Tab geöffnet</div>
    <div class="s-card__price">EUR 189,99</div>
    <div class="s-card__subtitle">Neu | Gewerblich</div>
    <img src="https://i.ebayimg.com/x-s-l500.webp"/>
    <div class="s-card__attribute-row">EUR 189,99</div>
    <div class="s-card__attribute-row">Gratis Lieferung</div>
  </li>
  <li class="s-card">
    <a href="/itm/998877665544?epid=1">Zum Angebot</a>
    <div class="s-card__title">Neues Angebot Sony XM5 gebraucht</div>
    <div class="s-card__price">EUR 150,00</div>
    <div class="s-card__subtitle">Gebraucht | Privat</div>
    <img data-src="https://i.ebayimg.com/y-s-l140.webp"/>
    <div class="s-card__attribute-row">+EUR 6,90 · 1-2 Tage Lieferung</div>
  </li>
</ul>
"""


# --- Parser ---


def test_parse_active_listings_extracts_fields_and_skips_placeholder():
    """Platzhalter ohne Item-Link entfällt; Titel/ID/URL/Preis/Zustand/Versand werden geparst."""
    previews = ebay_active.parse_active_listings(_ACTIVE_HTML)
    assert len(previews) == 2

    first = previews[0]
    assert first.external_id == "123456789012"
    assert first.title == "Sony WH-1000XM5 Schwarz"  # Tab-Hinweis entfernt
    assert first.url == "https://www.ebay.de/itm/123456789012"  # Tracking-Parameter entfernt
    assert first.price == 189.99
    assert first.condition == "Neu"
    assert first.seller_type == "Gewerblich"
    assert first.image_url == "https://i.ebayimg.com/x-s-l500.webp"
    assert first.shipping_cost == "Gratis Lieferung"

    second = previews[1]
    assert second.external_id == "998877665544"
    assert second.title == "Sony XM5 gebraucht"  # "Neues Angebot" entfernt
    assert second.condition == "Gebraucht"
    assert second.seller_type == "Privat"
    assert second.image_url == "https://i.ebayimg.com/y-s-l140.webp"  # aus data-src
    assert second.shipping_cost == "+EUR 6,90 · 1-2 Tage Lieferung"


# --- URL-Bau ---


def test_build_active_search_url_has_price_and_sort():
    """URL enthält Suchbegriff, Preisgrenzen (_udlo/_udhi) und Sortierung 'neu zuerst'."""
    url = ebay_active.build_active_search_url("sony wh-1000xm5", 100, 250)
    assert url.startswith("https://www.ebay.de/sch/i.html?")
    assert "_nkw=sony+wh-1000xm5" in url
    assert "_udlo=100" in url and "_udhi=250" in url
    assert "_sop=10" in url  # neu eingestellt


def test_build_active_search_url_without_price():
    """Ohne Preisgrenzen fehlen _udlo/_udhi, Suchbegriff und Sortierung bleiben."""
    url = ebay_active.build_active_search_url("bürostuhl")
    assert "_udlo" not in url and "_udhi" not in url
    assert "_nkw=b%C3%BCrostuhl" in url


# --- Fetch mit Proxy-Fallback ---


def test_fetch_uses_direct_when_usable():
    """Ist der direkte Abruf brauchbar, wird der Proxy nicht bemüht."""
    with (
        patch.object(ebay_active, "_fetch_direct", return_value=(200, _ACTIVE_HTML)),
        patch.object(ebay_active, "_fetch_via_proxy") as proxy,
    ):
        status, html = ebay_active.fetch_active_html("https://www.ebay.de/sch/i.html?_nkw=x")
    assert status == 200
    proxy.assert_not_called()


def test_fetch_falls_back_to_proxy_when_blocked():
    """Blockiert der direkte Abruf (403), liefert der Proxy das Ergebnis."""
    with (
        patch.object(ebay_active, "_fetch_direct", return_value=(403, "")),
        patch.object(ebay_active, "_fetch_via_proxy", return_value=(200, _ACTIVE_HTML)) as proxy,
    ):
        status, html = ebay_active.fetch_active_html("https://www.ebay.de/sch/i.html?_nkw=x")
    assert status == 200 and "s-card" in html
    proxy.assert_called_once()


def test_fetch_returns_direct_result_when_no_proxy():
    """Ohne konfigurierten Proxy bleibt es beim (blockierten) Direktergebnis."""
    with (
        patch.object(ebay_active, "_fetch_direct", return_value=(403, "")),
        patch.object(ebay_active, "_fetch_via_proxy", return_value=None),
    ):
        status, _ = ebay_active.fetch_active_html("https://www.ebay.de/sch/i.html?_nkw=x")
    assert status == 403


# --- EbayScraper (Plattform-Adapter) ---


def test_ebay_build_search_url_ignores_location():
    """eBay ist bundesweit → PLZ/Radius werden ignoriert, Preis/Begriff landen in der URL."""
    scraper = get_platform("ebay").scraper
    url = scraper.build_search_url(
        SearchParams(query="sony xm5", postal_code="50667", radius_km=50, max_price=200)
    )
    assert "_nkw=sony+xm5" in url and "_udhi=200" in url
    assert "locationStr" not in url and "radiusKm" not in url


def test_ebay_build_search_url_rejects_empty_query():
    """Leerer Suchbegriff ist ein Fehler."""
    scraper = get_platform("ebay").scraper
    with pytest.raises(ValueError, match="leer"):
        scraper.build_search_url(SearchParams(query="   "))


def test_ebay_collect_previews_parses_fetched_html():
    """collect_previews holt die Trefferliste und parst die Vorschauen."""
    scraper = get_platform("ebay").scraper
    with patch.object(ebay_active, "fetch_active_html", return_value=(200, _ACTIVE_HTML)):
        previews = scraper.collect_previews("https://www.ebay.de/sch/i.html?_nkw=x")
    assert len(previews) == 2


def test_ebay_collect_previews_returns_empty_when_blocked():
    """Bei Blockade (kein brauchbares HTML) leere Liste statt Exception."""
    scraper = get_platform("ebay").scraper
    with patch.object(ebay_active, "fetch_active_html", return_value=(403, "")):
        assert scraper.collect_previews("https://www.ebay.de/sch/i.html?_nkw=x") == []


def test_ebay_build_details_maps_previews_without_fetch():
    """build_details mappt die vollständigen Kartendaten ohne weiteren Abruf zu Details."""
    scraper = get_platform("ebay").scraper
    previews = ebay_active.parse_active_listings(_ACTIVE_HTML)
    details = scraper.build_details(previews)
    assert len(details) == 2
    first = details[0]
    assert first.external_id == "123456789012"
    assert first.price == 189.99
    assert first.condition == "Neu"
    assert first.seller_type == "Gewerblich"
    assert first.image_urls == ["https://i.ebayimg.com/x-s-l500.webp"]
    assert first.description is None  # eBay-Karten liefern keine Beschreibung
