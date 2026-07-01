"""Tests für die eBay-Sold-Marktwert-Referenz (Parser, Median, Endpunkt)."""

from unittest.mock import patch

import pytest

from app.scraper import ebay_sold
from app.scraper.ebay_sold import SoldListing, parse_sold_listings
from app.services.price_reference import EbayBlockedError, SoldReference, get_ebay_sold_reference

# Minimal-HTML, das die verifizierte eBay-Struktur nachbildet (inkl. Platzhalter-Item in USD).
_SOLD_HTML = """
<ul>
  <li class="s-card">
    <div class="s-card__title">Shop on eBay</div>
    <div class="s-card__price">$20.00</div>
  </li>
  <li class="s-card">
    <div class="s-card__caption">Verkauft 1. Jul 2026</div>
    <div class="s-card__title">Neues Angebot iPhone 15 Pro 256GB Titan Blau</div>
    <div class="s-card__price">EUR 609,00</div>
    <div class="s-card__subtitle">Gebraucht | Privat</div>
  </li>
  <li class="s-card">
    <div class="s-card__caption">Verkauft 30. Jun 2026</div>
    <div class="s-card__title">iPhone 15 Pro 256GB</div>
    <div class="s-card__price">EUR 675,31</div>
    <div class="s-card__subtitle">Gut - Refurbished | Gewerblich</div>
  </li>
</ul>
"""


def _html_with_prices(prices: list[str]) -> str:
    cards = "".join(
        f'<li class="s-card"><div class="s-card__caption">Verkauft 1. Jul 2026</div>'
        f'<div class="s-card__title">iPhone {i}</div>'
        f'<div class="s-card__price">EUR {p}</div>'
        f'<div class="s-card__subtitle">Gebraucht | Privat</div></li>'
        for i, p in enumerate(prices)
    )
    return f"<ul>{cards}</ul>"


# --- Parser ---


def test_parse_sold_listings_extracts_fields_and_skips_placeholder():
    """Platzhalter (Shop on eBay/USD) wird übersprungen; Felder werden geparst."""
    listings = parse_sold_listings(_SOLD_HTML)
    assert len(listings) == 2  # Platzhalter raus

    first = listings[0]
    assert first.title == "iPhone 15 Pro 256GB Titan Blau"  # "Neues Angebot" entfernt
    assert first.price == 609.0
    assert first.currency == "EUR"
    assert first.sold_date == "1. Jul 2026"
    assert first.condition == "Gebraucht"
    assert first.seller_type == "Privat"

    assert listings[1].price == 675.31
    assert listings[1].condition == "Gut - Refurbished"


def test_parse_price_handles_formats():
    """'EUR 1.299,00' und '609,00 €' werden korrekt geparst; USD ergibt None."""
    assert ebay_sold._parse_price("EUR 1.299,00") == (1299.0, "EUR")
    assert ebay_sold._parse_price("609,00 €") == (609.0, "EUR")
    assert ebay_sold._parse_price("$20.00") == (None, None)


# --- Median-Aggregation (fetch dort patchen, wo der Service ihn nutzt) ---


def test_get_ebay_sold_reference_computes_median():
    """Median/Spanne/Count werden aus den EUR-Verkäufen berechnet."""
    html = _html_with_prices(["100,00", "200,00", "300,00", "400,00", "500,00"])
    with patch("app.services.price_reference.fetch_sold_html", return_value=(200, html)):
        ref = get_ebay_sold_reference("iphone")
    assert ref is not None
    assert ref.median == 300.0
    assert ref.low == 100.0
    assert ref.high == 500.0
    assert ref.count == 5
    assert ref.currency == "EUR"


def test_get_ebay_sold_reference_too_few_returns_none():
    """Weniger als MIN_COMPARISONS Vergleiche → None (kein belastbarer Median)."""
    html = _html_with_prices(["100,00", "200,00"])
    with patch("app.services.price_reference.fetch_sold_html", return_value=(200, html)):
        assert get_ebay_sold_reference("iphone") is None


def test_get_ebay_sold_reference_blocked_raises():
    """403/Netzwerkfehler → EbayBlockedError."""
    with (
        patch("app.services.price_reference.fetch_sold_html", return_value=(403, "")),
        pytest.raises(EbayBlockedError),
    ):
        get_ebay_sold_reference("iphone")


# --- Endpunkt (Service gemockt, kein echter eBay-Abruf) ---


@patch("app.routes.api.ads.get_ebay_sold_reference")
def test_market_reference_endpoint_success(mock_ref, client, sample_ads):
    """POST liefert Median + Vergleiche für die Anzeige."""
    mock_ref.return_value = SoldReference(
        query="Rode PodMic",
        currency="EUR",
        median=95.0,
        low=70.0,
        high=130.0,
        count=12,
        listings=[SoldListing("Rode PodMic", 95.0, "EUR", "1. Jul 2026", "Gebraucht", "Privat")],
    )
    response = client.post(f"/ads/{sample_ads[0].id}/market-reference")
    assert response.status_code == 200
    body = response.json()
    assert body["median"] == 95.0
    assert body["count"] == 12
    assert len(body["comps"]) == 1
    assert body["comps"][0]["title"] == "Rode PodMic"


@patch("app.routes.api.ads.get_ebay_sold_reference", side_effect=EbayBlockedError("403"))
def test_market_reference_endpoint_blocked_returns_502(_mock_ref, client, sample_ads):
    """Blockierter eBay-Abruf → 502 mit klarer Meldung."""
    response = client.post(f"/ads/{sample_ads[0].id}/market-reference")
    assert response.status_code == 502


def test_market_reference_endpoint_404_for_unknown_ad(client):
    """Unbekannte Anzeige → 404."""
    response = client.post("/ads/999999/market-reference")
    assert response.status_code == 404
