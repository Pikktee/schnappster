"""Tests for the HTML parser."""

from pathlib import Path

from app.scraper.parser import (
    _parse_price,
    _split_locality,
    parse_ad_detail,
    parse_search_results,
)

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
    # Description preserves line breaks from <br> (from fixture)
    assert ad.description is not None
    assert "\n" in ad.description
    assert "Enthalten sind:" in ad.description
    assert "Rode PodMic" in ad.description
    # Kategorie und Preis-Typ aus JS-Block (VB-Anzeige)
    assert ad.category_l1 == "Multimedia_Elektronik"
    assert ad.category_l2 == "Audio_Hifi"
    assert ad.price_type == "NEGOTIABLE"
    assert ad.price_raw is not None
    assert "110" in ad.price_raw


def test_parse_ad_detail_for_free_ad():
    """Zu-verschenken-Fixture: price None, Kategorie Verschenken & Tauschen."""
    html = (FIXTURES_DIR / "ad-for-free.html").read_text()
    ad = parse_ad_detail(
        html,
        url="https://www.kleinanzeigen.de/s-anzeige/schneeanzug-winteranzug-116/3350443162-192-156",
        external_id="3350443162",
    )

    assert ad is not None
    assert "Schneeanzug" in ad.title
    assert ad.price is None
    assert ad.category_l1 == "Zu_verschenken_Tauschen"
    assert ad.category_l2 == "Zu_verschenken"
    assert ad.price_type is None or ad.price_type == ""


def test_parse_ad_detail_for_vb_with_price():
    """Anzeige mit VB und angegebenem Preis (z.B. 1.999 € VB): Preis und Kategorie werden geparst."""
    html = (FIXTURES_DIR / "ad-with-vb-and-price.html").read_text()
    ad = parse_ad_detail(
        html,
        url="https://www.kleinanzeigen.de/s-anzeige/davinci-brautkleid-gr-38-40-mit-ueberrock-schleier/3305703921-154-9293",
        external_id="3305703921",
    )

    assert ad is not None
    assert "Davinci" in ad.title
    assert ad.price == 1999.0
    assert ad.category_l1 == "Mode_Beauty"
    assert ad.category_l2 == "Kleidung_Damen"
    assert ad.price_type == "NEGOTIABLE"
    assert ad.price_raw is not None
    assert "VB" in ad.price_raw


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


# --- Search results parsing ---


def test_parse_search_results_ignores_alternative_ads_only_page():
    """Eine Seite mit nur 'Alternativen in der Umgebung' liefert keine Treffer."""
    html = (FIXTURES_DIR / "ad-with-no-results.html").read_text()
    previews = parse_search_results(html)

    assert previews == []


def test_parse_search_results_ignores_alternative_ads_below_real_results():
    """Treffer unterhalb von 'Alternativen in der Umgebung' werden ignoriert."""
    html = """
    <html><body>
        <ul>
            <li class="ad-listitem">
                <a href="/s-anzeige/echte-anzeige/123456789-123-456">
                    Echte Anzeige vor Alternativen
                </a>
            </li>
        </ul>
        <h2>Alternative Anzeigen in der Umgebung</h2>
        <ul>
            <li class="ad-listitem">
                <a href="/s-anzeige/alternative-anzeige/987654321-123-456">
                    Alternative Anzeige
                </a>
            </li>
        </ul>
    </body></html>
    """

    previews = parse_search_results(html)

    assert len(previews) == 1
    assert previews[0].external_id == "123456789"


def test_parse_search_results_parses_all_items_without_alternative_block():
    """Ohne Alternativ-Block werden alle Listeneinträge geparst."""
    html = """
    <html><body>
        <ul>
            <li class="ad-listitem">
                <a href="/s-anzeige/erste-anzeige/111111111-123-456">
                    Erste Anzeige
                </a>
            </li>
            <li class="ad-listitem">
                <a href="/s-anzeige/zweite-anzeige/222222222-123-456">
                    Zweite Anzeige
                </a>
            </li>
        </ul>
    </body></html>
    """

    previews = parse_search_results(html)

    assert len(previews) == 2
    assert {p.external_id for p in previews} == {"111111111", "222222222"}
