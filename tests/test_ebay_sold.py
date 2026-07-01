"""Tests für die eBay-Sold-Marktwert-Referenz: Parser, Median, Cache, Score-Anker."""

from unittest.mock import patch

import pytest

from app.scraper import ebay_sold
from app.scraper.ebay_sold import parse_sold_listings
from app.services.deal_analysis import (
    ComparisonCandidate,
    ComparisonJudgement,
    ProductExtraction,
    build_market_estimate,
)
from app.services.price_reference import (
    EbayBlockedError,
    get_ebay_sold_reference,
    get_market_reference_cached,
    reset_cache,
)

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
    assert len(listings) == 2

    first = listings[0]
    assert first.title == "iPhone 15 Pro 256GB Titan Blau"  # "Neues Angebot" entfernt
    assert first.price == 609.0
    assert first.currency == "EUR"
    assert first.sold_date == "1. Jul 2026"
    assert first.condition == "Gebraucht"
    assert first.seller_type == "Privat"
    assert listings[1].price == 675.31


def test_parse_price_handles_formats():
    """'EUR 1.299,00' und '609,00 €' werden korrekt geparst; USD ergibt None."""
    assert ebay_sold._parse_price("EUR 1.299,00") == (1299.0, "EUR")
    assert ebay_sold._parse_price("609,00 €") == (609.0, "EUR")
    assert ebay_sold._parse_price("$20.00") == (None, None)


# --- Median-Aggregation ---


def test_get_ebay_sold_reference_computes_median():
    """Median/Spanne/Count werden aus den EUR-Verkäufen berechnet."""
    html = _html_with_prices(["100,00", "200,00", "300,00", "400,00", "500,00"])
    with patch("app.services.price_reference.fetch_sold_html", return_value=(200, html)):
        ref = get_ebay_sold_reference("iphone")
    assert ref is not None
    assert ref.median == 300.0
    assert (ref.low, ref.high, ref.count) == (100.0, 500.0, 5)


def test_get_ebay_sold_reference_too_few_returns_none():
    """Weniger als MIN_COMPARISONS Vergleiche → None."""
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


# --- Cache + Cooldown (für die Pipeline) ---


def test_get_market_reference_cached_uses_cache():
    """Zweiter Aufruf mit gleichem Schlüssel kommt aus dem Cache (kein erneuter Abruf)."""
    reset_cache()
    html = _html_with_prices(["100,00", "200,00", "300,00"])
    with patch("app.services.price_reference.fetch_sold_html", return_value=(200, html)) as mock:
        first = get_market_reference_cached("iPhone")
        second = get_market_reference_cached("iphone")  # gleicher Schlüssel (case-insensitiv)
    assert first is not None and second is not None
    assert mock.call_count == 1


def test_get_market_reference_cached_cooldown_after_block():
    """Nach einem Block wird eBay im Cooldown nicht erneut abgefragt (returnt None)."""
    reset_cache()
    with patch("app.services.price_reference.fetch_sold_html", return_value=(403, "")) as mock:
        first = get_market_reference_cached("blocked")
        second = get_market_reference_cached("blocked")
    assert first is None and second is None
    assert mock.call_count == 1  # zweiter Aufruf durch Cooldown unterdrückt
    reset_cache()


# --- Score-Anker: build_market_estimate bevorzugt den Sold-Median ---


def test_build_market_estimate_prefers_sold_median():
    """Liegt ein eBay-Sold-Median vor, ist er der Marktwert-Anker (statt Suchvergleich)."""
    estimate = build_market_estimate(
        100.0,
        ProductExtraction(product_key="x"),
        [ComparisonCandidate(title="a", price=999.0)],
        [ComparisonJudgement(candidate_index=0, comparable=True, adjusted_price=999.0)],
        sold_median=140.0,
        sold_low=120.0,
        sold_high=170.0,
        sold_count=10,
    )
    assert estimate.estimated_market_price == 140.0
    assert estimate.comparison_count == 10
    assert "eBay-Verkäufen" in estimate.comparison_summary
    assert estimate.price_delta_percent == 28.6  # (140-100)/140


def test_build_market_estimate_falls_back_without_sold():
    """Ohne Sold-Median greift der Median der Suchvergleiche."""
    prices = [200.0, 220.0, 240.0]
    candidates = [ComparisonCandidate(title=str(p), price=p) for p in prices]
    judgements = [
        ComparisonJudgement(candidate_index=i, comparable=True, adjusted_price=c.price)
        for i, c in enumerate(candidates)
    ]
    estimate = build_market_estimate(
        150.0, ProductExtraction(product_key="x"), candidates, judgements
    )
    assert estimate.estimated_market_price == 220.0  # Median
    assert "Vergleichen" in estimate.comparison_summary
