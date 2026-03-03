from pathlib import Path

from app.scraper.parser import parse_ad_detail

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_ad_detail():
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
    assert ad.seller_rating == "TOP"
    assert ad.seller_is_friendly is True
    assert ad.seller_is_reliable is True
    assert "Privat" in (ad.seller_type or "")
    assert ad.seller_active_since == "03.10.2025"
    assert ad.seller_url is not None
    assert "155221098" in ad.seller_url
