"""Tests für die Preis-Extraktion: Kandidaten, generisches Parsing, Locator-Wiederfindung."""

import pytest

from app.services.price_extractor import (
    extract_candidates,
    extract_price,
    parse_price_value,
    parse_title,
)

# --- Repräsentatives HTML (bildet reale Muster nach) ---
JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{"@type":"Product","name":"Bücherregal",
 "offers":{"@type":"Offer","price":"49.99","priceCurrency":"EUR"}}
</script>
</head><body><h1>Bücherregal</h1></body></html>
"""

META_HTML = """
<html><head>
<meta itemprop="price" content="129.00">
<meta itemprop="priceCurrency" content="EUR">
<title>Stuhl</title>
</head><body></body></html>
"""

VISIBLE_HTML = """
<html><body>
<p class="product-price">19,95 €</p>
<span>Beschreibung ohne Preis</span>
</body></html>
"""

NOISE_HTML = """
<html><body>
<span class="price">49,99 €</span>
<span class="price-integer">49</span>
<div>Nur kurz: 10€ Rabatt mit FUSSBALL für ein langes Banner hier drin</div>
</body></html>
"""


# --- parse_price_value ---
@pytest.mark.parametrize(
    "text,value,currency",
    [
        ("1.234,56 €", 1234.56, "EUR"),
        ("$1,234.56", 1234.56, "USD"),
        ("69.00 USD", 69.0, "USD"),
        ("£51.77", 51.77, "GBP"),
        ("27,99€", 27.99, "EUR"),
        ("1 299,00 €", 1299.0, "EUR"),
        ("CHF 89.90", 89.90, "CHF"),
        ("", None, None),
        ("kostenlos", None, None),
    ],
)
def test_parse_price_value(text, value, currency):
    assert parse_price_value(text) == (value, currency)


# --- Kandidaten-Extraktion je Quelle ---
def test_extract_jsonld_candidate_and_roundtrip():
    candidates = extract_candidates(JSONLD_HTML)
    assert candidates, "kein Kandidat gefunden"
    first = candidates[0]
    assert first.value == 49.99
    assert first.currency == "EUR"
    assert first.source == "jsonld"
    assert extract_price(JSONLD_HTML, first.locator)[0] == 49.99


def test_extract_meta_candidate_and_roundtrip():
    candidates = extract_candidates(META_HTML)
    meta = next(c for c in candidates if c.source == "meta")
    assert meta.value == 129.0
    assert meta.currency == "EUR"
    assert extract_price(META_HTML, meta.locator)[0] == 129.0


def test_extract_visible_candidate_and_roundtrip():
    candidates = extract_candidates(VISIBLE_HTML)
    visible = next(c for c in candidates if c.source == "visible")
    assert visible.value == 19.95
    assert visible.currency == "EUR"
    assert extract_price(VISIBLE_HTML, visible.locator)[0] == 19.95


# Mehrere Preise teilen sich dieselbe generische Klasse (Muster: Amazon span.a-offscreen).
AMBIGUOUS_HTML = """
<html><body>
  <div id="corePrice">
    <span class="a-offscreen">23,90 €</span>
  </div>
  <div id="accessory">
    <span class="a-offscreen">7,99 €</span>
  </div>
  <div id="rrp">
    <span class="a-offscreen">29,99 €</span>
  </div>
</body></html>
"""


def test_visible_selector_is_disambiguated_by_ancestor():
    """Jeder gleich-klassige Preis bekommt einen eigenen, eindeutig wiederfindbaren Selektor."""
    candidates = extract_candidates(AMBIGUOUS_HTML)
    by_value = {c.value: c for c in candidates}
    assert {23.9, 7.99, 29.99} <= set(by_value)
    # Der gewählte Preis muss per gespeichertem Locator exakt wiedergefunden werden,
    # nicht bloß der erste Treffer der generischen Klasse.
    for value, cand in by_value.items():
        assert extract_price(AMBIGUOUS_HTML, cand.locator)[0] == value


def test_css_disambiguation_picks_value_closest_to_reference():
    """Bleibt der Selektor mehrdeutig, gewinnt der Treffer nahe am ursprünglich gewählten Wert."""
    html = """
    <html><body>
      <span class="a-offscreen">7,99 €</span>
      <span class="a-offscreen">24,50 €</span>
    </body></html>
    """
    # Generischer Selektor trifft beide; Referenzwert 23,90 → näher an 24,50 als an 7,99.
    locator = {"strategy": "css", "selector": "span.a-offscreen", "value": 23.9}
    assert extract_price(html, locator)[0] == 24.5


def test_visible_filters_split_digits_and_long_banners():
    values = {c.value for c in extract_candidates(NOISE_HTML)}
    assert 49.99 in values
    # gesplittete Ziffer "49" ohne Währung und langer Rabatt-Banner werden gefiltert
    assert 49.0 not in values
    assert 10.0 not in values


def test_dedupe_prefers_structured_source():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"offers":{"price":"49.99","priceCurrency":"EUR"}}</script>
    </head><body><span class="price">49,99 €</span></body></html>
    """
    matching = [c for c in extract_candidates(html) if c.value == 49.99]
    assert len(matching) == 1
    assert matching[0].source == "jsonld"


# --- Edge-Cases ---
def test_no_price_returns_empty():
    assert extract_candidates("<html><body>Kein Preis</body></html>") == []
    assert extract_candidates("") == []


def test_extract_price_missing_or_invalid_locator():
    html = "<html><body><span class='price'>10 €</span></body></html>"
    assert extract_price(html, {"strategy": "css", "selector": "#nope"})[0] is None
    # ungültiger Selektor darf nicht crashen
    assert extract_price(html, {"strategy": "css", "selector": "###"})[0] is None
    assert extract_price(html, {})[0] is None


def test_jsonld_fallback_when_path_changed():
    """Hat sich die Struktur geändert, greift der Fallback (erster Preis-Treffer)."""
    html = (
        '<html><head><script type="application/ld+json">'
        '{"offers":{"price":"42.00"}}</script></head></html>'
    )
    # gespeicherter Pfad zeigt ins Leere, Fallback findet trotzdem den Preis
    value, _ = extract_price(html, {"strategy": "jsonld", "script_index": 0, "path": ["x", "y"]})
    assert value == 42.0


def test_parse_title():
    assert parse_title("<html><head><title>Mein Produkt</title></head></html>") == "Mein Produkt"
    og = '<html><head><meta property="og:title" content="OG Titel"></head></html>'
    assert parse_title(og) == "OG Titel"
