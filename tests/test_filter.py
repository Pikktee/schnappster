"""Tests für die Anzeigen-Filterlogik im ScraperService."""

from app.models.adsearch import AdSearch
from app.scraper.parser import ScrapedAdDetail
from app.services.scraper import ScraperService


def _make_detail(**kwargs) -> ScrapedAdDetail:
    """Erstellt ein ScrapedAdDetail mit optionalen Overrides und Defaults."""
    defaults = {
        "external_id": "123",
        "title": "Test Ad",
        "url": "https://example.com/ad/123",
        "price": 50.0,
        "seller_type": "Privat",
        "seller_rating": 2,
    }
    defaults.update(kwargs)
    return ScrapedAdDetail(**defaults)


def _make_adsearch(**kwargs) -> AdSearch:
    """Erstellt einen AdSearch mit optionalen Overrides und Defaults."""
    defaults = {
        "owner_id": "00000000-0000-0000-0000-000000000001",
        "name": "Test",
        "url": "https://example.com",
        "min_price": None,
        "max_price": None,
        "blacklist_keywords": None,
    }
    defaults.update(kwargs)
    return AdSearch(**defaults)


# --- Price filter ---


def test_filter_passes_when_price_in_range():
    """Anzeige bleibt, wenn Preis zwischen min und max liegt."""
    detail = _make_detail(price=50.0)
    adsearch = _make_adsearch(min_price=20.0, max_price=100.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_rejects_price_below_minimum():
    """Anzeige wird gefiltert, wenn Preis unter min_price liegt."""
    detail = _make_detail(price=10.0)
    adsearch = _make_adsearch(min_price=20.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "Minimum" in reason


def test_filter_rejects_price_above_maximum():
    """Anzeige wird gefiltert, wenn Preis über max_price liegt."""
    detail = _make_detail(price=300.0)
    adsearch = _make_adsearch(max_price=200.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "Maximum" in reason


def test_filter_passes_when_no_price_limits():
    """Anzeige bleibt, wenn der Suchauftrag keine Preisgrenzen hat."""
    detail = _make_detail(price=9999.0)
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_passes_when_price_is_none():
    """Ad with no price (nicht Zu-verschenken) wird gefiltert."""
    detail = _make_detail(price=None)
    adsearch = _make_adsearch(min_price=20.0, max_price=200.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "Kein Preis" in reason


# --- Blacklist filter ---


def test_filter_rejects_blacklisted_title():
    """Anzeige wird gefiltert, wenn Blacklist-Keyword im Titel vorkommt."""
    detail = _make_detail(title="Rode PodMic defekt")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "defekt" in reason


def test_filter_rejects_blacklisted_description():
    """Anzeige wird gefiltert, wenn Blacklist-Keyword in der Beschreibung vorkommt."""
    detail = _make_detail(description="Für Bastler, nicht funktionsfähig")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "bastler" in reason


def test_filter_passes_when_no_blacklist_match():
    """Anzeige bleibt, wenn kein Blacklist-Keyword in Titel oder Beschreibung."""
    detail = _make_detail(title="Rode PodMic neuwertig")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_passes_when_no_blacklist():
    """Anzeige mit Keyword im Titel bleibt, wenn der Suchauftrag keine Blacklist hat."""
    detail = _make_detail(title="Rode PodMic defekt")
    adsearch = _make_adsearch(blacklist_keywords=None)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_blacklist_case_insensitive():
    """Blacklist-Abgleich ist case-insensitiv."""
    detail = _make_detail(title="DEFEKTES Mikrofon")
    adsearch = _make_adsearch(blacklist_keywords="defekt")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None


# --- Commercial seller filter ---


def test_filter_rejects_commercial_seller():
    """Anzeige wird gefiltert, wenn Verkäufer gewerblich ist und die globale Einstellung Gewerbe ausschließt."""
    detail = _make_detail(seller_type="Gewerblich")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 0)
    assert reason is not None
    assert "Gewerblich" in reason


def test_filter_passes_private_seller_when_excluding_commercial():
    """Privatverkäufer bleibt, wenn gewerbliche Verkäufer ausgeschlossen sind."""
    detail = _make_detail(seller_type="Privat")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 0)
    assert reason is None


def test_filter_passes_commercial_when_not_excluding():
    """Gewerblicher Verkäufer bleibt, wenn die Ausschluss-Einstellung false ist."""
    detail = _make_detail(seller_type="Gewerblich")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


# --- Seller rating filter ---


def test_filter_rejects_low_rating():
    """Anzeige wird gefiltert, wenn Verkäufer-Rating unter dem globalen Minimum liegt."""
    detail = _make_detail(seller_rating=0)  # Na ja
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)  # min=TOP
    assert reason is not None
    assert "Rating" in reason


def test_filter_passes_matching_rating():
    """Anzeige bleibt, wenn das Verkäufer-Rating dem Minimum entspricht."""
    detail = _make_detail(seller_rating=2)  # TOP
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)  # min=TOP
    assert reason is None


def test_filter_passes_higher_rating():
    """Anzeige bleibt, wenn das Verkäufer-Rating über dem Minimum liegt."""
    detail = _make_detail(seller_rating=2)  # TOP
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 1)  # min=OK
    assert reason is None


def test_filter_passes_when_no_rating():
    """Anzeige ohne Verkäufer-Rating bleibt (kein Rating-Filter angewendet)."""
    detail = _make_detail(seller_rating=None)
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)
    assert reason is None


# --- Combined filters ---


def test_filter_rejects_on_first_matching_rule():
    """Bei mehreren zutreffenden Regeln wird der erste Grund (z. B. Preis) zurückgegeben."""
    detail = _make_detail(price=5.0, title="Defektes Mikrofon", seller_type="Gewerblich")
    adsearch = _make_adsearch(min_price=20.0, blacklist_keywords="defekt")
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 2)
    assert reason is not None
    # Preisfilter läuft zuerst
    assert "Minimum" in reason
