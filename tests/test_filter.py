"""Tests for the ad filter logic in ScraperService."""

from app.models.adsearch import AdSearch
from app.scraper.parser import ScrapedAdDetail
from app.services.scraper import ScraperService


def _make_detail(**kwargs) -> ScrapedAdDetail:
    """Create a ScrapedAdDetail with optional overrides and defaults."""
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
    """Create an AdSearch with optional overrides and defaults."""
    defaults = {
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
    """Ad passes when price is within min/max."""
    detail = _make_detail(price=50.0)
    adsearch = _make_adsearch(min_price=20.0, max_price=100.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_rejects_price_below_minimum():
    """Ad is filtered out when price below min_price."""
    detail = _make_detail(price=10.0)
    adsearch = _make_adsearch(min_price=20.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "Minimum" in reason


def test_filter_rejects_price_above_maximum():
    """Ad is filtered out when price above max_price."""
    detail = _make_detail(price=300.0)
    adsearch = _make_adsearch(max_price=200.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "Maximum" in reason


def test_filter_passes_when_no_price_limits():
    """Ad passes when AdSearch has no min/max price."""
    detail = _make_detail(price=9999.0)
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_passes_when_price_is_none():
    """Ad with no price passes when within optional limits (VB case)."""
    detail = _make_detail(price=None)
    adsearch = _make_adsearch(min_price=20.0, max_price=200.0)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


# --- Blacklist filter ---


def test_filter_rejects_blacklisted_title():
    """Ad is filtered when blacklist keyword appears in title."""
    detail = _make_detail(title="Rode PodMic defekt")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "defekt" in reason


def test_filter_rejects_blacklisted_description():
    """Ad is filtered when blacklist keyword appears in description."""
    detail = _make_detail(description="Für Bastler, nicht funktionsfähig")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None
    assert "bastler" in reason


def test_filter_passes_when_no_blacklist_match():
    """Ad passes when no blacklist keyword in title or description."""
    detail = _make_detail(title="Rode PodMic neuwertig")
    adsearch = _make_adsearch(blacklist_keywords="defekt,bastler")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_passes_when_no_blacklist():
    """Ad with keyword in title passes when AdSearch has no blacklist."""
    detail = _make_detail(title="Rode PodMic defekt")
    adsearch = _make_adsearch(blacklist_keywords=None)
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


def test_filter_blacklist_case_insensitive():
    """Blacklist matching is case-insensitive."""
    detail = _make_detail(title="DEFEKTES Mikrofon")
    adsearch = _make_adsearch(blacklist_keywords="defekt")
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is not None


# --- Commercial seller filter ---


def test_filter_rejects_commercial_seller():
    """Ad is filtered when seller is commercial and global setting excludes commercial."""
    detail = _make_detail(seller_type="Gewerblich")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 0)
    assert reason is not None
    assert "Gewerblich" in reason


def test_filter_passes_private_seller_when_excluding_commercial():
    """Private seller passes when commercial sellers are excluded."""
    detail = _make_detail(seller_type="Privat")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 0)
    assert reason is None


def test_filter_passes_commercial_when_not_excluding():
    """Commercial seller passes when exclusion setting is false."""
    detail = _make_detail(seller_type="Gewerblich")
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 0)
    assert reason is None


# --- Seller rating filter ---


def test_filter_rejects_low_rating():
    """Ad is filtered when seller rating below global minimum."""
    detail = _make_detail(seller_rating=0)  # Na ja
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)  # min=TOP
    assert reason is not None
    assert "Rating" in reason


def test_filter_passes_matching_rating():
    """Ad passes when seller rating meets minimum."""
    detail = _make_detail(seller_rating=2)  # TOP
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)  # min=TOP
    assert reason is None


def test_filter_passes_higher_rating():
    """Ad passes when seller rating above minimum."""
    detail = _make_detail(seller_rating=2)  # TOP
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 1)  # min=OK
    assert reason is None


def test_filter_passes_when_no_rating():
    """Ad with no seller rating passes (no rating filter applied)."""
    detail = _make_detail(seller_rating=None)
    adsearch = _make_adsearch()
    reason = ScraperService._get_filter_reason(detail, adsearch, False, 2)
    assert reason is None


# --- Combined filters ---


def test_filter_rejects_on_first_matching_rule():
    """When multiple rules match, the first reason (e.g. price) is returned."""
    detail = _make_detail(price=5.0, title="Defektes Mikrofon", seller_type="Gewerblich")
    adsearch = _make_adsearch(min_price=20.0, blacklist_keywords="defekt")
    reason = ScraperService._get_filter_reason(detail, adsearch, True, 2)
    assert reason is not None
    # Price filter runs first
    assert "Minimum" in reason
