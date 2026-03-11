"""Tests for the HTML parser."""

from pathlib import Path

from app.scraper.parser import _parse_price, _split_locality, parse_ad_detail

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# --- Detail page parsing ---


def test_parse_ad_detail():
    """Parse full ad detail page fixture and assert all fields."""
    html = (FIXTURES_DIR / "ad.html").read_text()
    ad = parse_ad_detail(
        html,
        url="https://www.kleinanzeigen.de/s-anzeige/test/3341138442-172-17010",
        external_id="3341138442",
    )

    assert ad is not None
    assert ad.title == "Rode PodMic + Rode PSA1 Arm + Behringer Xenyx 302 USB"
    assert ad.price == 110.0
    assert ad.postal_code == "51105"
    assert ad.city == "Innenstadt - Poll"
    assert ad.condition == "Gut"
    assert ad.shipping_cost == "4,89 €"
    assert len(ad.image_urls) == 8
    assert ad.seller_name == "Tim"
    assert ad.seller_rating == 2  # TOP
    assert ad.seller_is_friendly is True
    assert ad.seller_is_reliable is True
    assert "Privat" in (ad.seller_type or "")
    assert ad.seller_active_since == "03.10.2025"
    assert ad.seller_url is not None
    assert "155221098" in ad.seller_url


def test_parse_ad_detail_returns_none_for_empty_html():
    """parse_ad_detail returns None for empty HTML."""
    ad = parse_ad_detail("", url="https://example.com", external_id="123")
    assert ad is None


def test_parse_ad_detail_returns_none_for_missing_title():
    """parse_ad_detail returns None when title element is missing."""
    html = "<html><body><div>No title here</div></body></html>"
    ad = parse_ad_detail(html, url="https://example.com", external_id="123")
    assert ad is None


# --- Rating parsing ---


def test_parse_rating_top():
    """Test parsing TOP rating from fixture."""
    html = (FIXTURES_DIR / "ad.html").read_text()
    ad = parse_ad_detail(
        html,
        url="https://www.kleinanzeigen.de/s-anzeige/test/3341138442-172-17010",
        external_id="3341138442",
    )
    assert ad is not None
    assert ad.seller_rating == 2


def test_parse_rating_ok():
    """Test parsing OK rating (icon-rating-tag-1)."""
    html = """
    <html><body>
        <h1 id="viewad-title">Test Ad</h1>
        <div id="viewad-profile-box">
            <span class="userbadge userbadges-profile-rating">
                <a class="userbadge-tag">
                    <i class="icon icon-smallest icon-rating-tag-1"></i>
                    OK&nbsp;Zufriedenheit</a>
            </span>
        </div>
    </body></html>
    """
    ad = parse_ad_detail(html, url="https://example.com", external_id="123")
    assert ad is not None
    assert ad.seller_rating == 1


def test_parse_rating_naja():
    """Test parsing 'Na ja' rating (icon-rating-tag-0)."""
    html = """
    <html><body>
        <h1 id="viewad-title">Test Ad</h1>
        <div id="viewad-profile-box">
            <span class="userbadge userbadges-profile-rating">
                <a class="userbadge-tag">
                    <i class="icon icon-smallest icon-rating-tag-0"></i>
                    Na&nbsp;ja&nbsp;Zufriedenheit</a>
            </span>
        </div>
    </body></html>
    """
    ad = parse_ad_detail(html, url="https://example.com", external_id="123")
    assert ad is not None
    assert ad.seller_rating == 0


def test_parse_rating_none_when_missing():
    """Test that rating is None when no rating badge exists."""
    html = """
    <html><body>
        <h1 id="viewad-title">Test Ad</h1>
        <div id="viewad-profile-box">
            <span class="userprofile-vip">
                <a href="/user/123">Seller Name</a>
            </span>
        </div>
    </body></html>
    """
    ad = parse_ad_detail(html, url="https://example.com", external_id="123")
    assert ad is not None
    assert ad.seller_rating is None


# --- Price parsing ---


def test_parse_price_simple():
    assert _parse_price("110 €") == 110.0


def test_parse_price_vb():
    assert _parse_price("110 € VB") == 110.0


def test_parse_price_decimal():
    assert _parse_price("110.00") == 110.0


def test_parse_price_german_decimal():
    assert _parse_price("1.234,56 €") == 1234.56


def test_parse_price_only_vb():
    assert _parse_price("VB") is None


def test_parse_price_empty():
    assert _parse_price("") is None


def test_parse_price_zu_verschenken():
    assert _parse_price("Zu verschenken") is None


# --- Locality splitting ---


def test_split_locality_with_postal_code():
    assert _split_locality("51105 Innenstadt - Poll") == ("51105", "Innenstadt - Poll")


def test_split_locality_without_postal_code():
    assert _split_locality("Berlin") == (None, "Berlin")


def test_split_locality_empty():
    assert _split_locality("") == (None, None)
