"""Tests für die Filterlogik im Scraper (VB vs. Zu verschenken)."""

from app.models.adsearch import AdSearch
from app.scraper.parser import ScrapedAdDetail
from app.services.scraper import ScraperService


def _make_adsearch() -> AdSearch:
    """Minimaler AdSearch ohne Preisgrenzen/Filter."""
    return AdSearch(
        name="Test-Suche",
        url="https://www.kleinanzeigen.de/s-test/kategorie/c123",
    )


def test_get_filter_reason_excludes_vb_ads_without_price():
    """Anzeigen mit ausschließlich VB (ohne angegebenen Preis) werden gefiltert."""
    detail = ScrapedAdDetail(
        external_id="1",
        title="Test VB",
        url="https://www.kleinanzeigen.de/s-anzeige/test/1-1-1",
        price=None,
        price_raw="VB",
        price_type="NEGOTIABLE",
        category_l1="Multimedia_Elektronik",
        category_l2="Audio_Hifi",
    )

    reason = ScraperService._get_filter_reason(
        detail=detail,
        adsearch=_make_adsearch(),
        exclude_commercial=False,
        min_rating=0,
    )

    assert reason is not None
    assert "VB-Anzeige" in reason


def test_get_filter_reason_keeps_vb_ads_with_price():
    """Anzeigen mit VB und angegebenem Preis (z.B. '1.999 € VB') werden nicht gefiltert."""
    detail = ScrapedAdDetail(
        external_id="1",
        title="Test VB mit Preis",
        url="https://www.kleinanzeigen.de/s-anzeige/test/1-1-1",
        price=1999.0,
        price_raw="1.999 € VB",
        price_type="NEGOTIABLE",
        category_l1="Mode_Beauty",
        category_l2="Kleidung_Damen",
    )

    reason = ScraperService._get_filter_reason(
        detail=detail,
        adsearch=_make_adsearch(),
        exclude_commercial=False,
        min_rating=0,
    )

    assert reason is None


def test_get_filter_reason_keeps_zu_verschenken_ads():
    """Zu-verschenken-Anzeigen (Kategorie Verschenken & Tauschen) werden nicht gefiltert."""
    detail = ScrapedAdDetail(
        external_id="2",
        title="Zu verschenken Artikel",
        url="https://www.kleinanzeigen.de/s-anzeige/test/2-2-2",
        price=None,
        price_raw=None,
        price_type=None,
        category_l1="Zu_verschenken_Tauschen",
        category_l2="Zu_verschenken",
    )

    reason = ScraperService._get_filter_reason(
        detail=detail,
        adsearch=_make_adsearch(),
        exclude_commercial=False,
        min_rating=0,
    )

    assert reason is None


def test_get_filter_reason_excludes_ads_without_price_and_not_zu_verschenken():
    """Anzeigen ohne Preis und ohne Zu-verschenken-Kategorie werden gefiltert."""
    detail = ScrapedAdDetail(
        external_id="3",
        title="Ohne Preis",
        url="https://www.kleinanzeigen.de/s-anzeige/test/3-3-3",
        price=None,
        price_raw="Preis auf Anfrage",
        price_type=None,
        category_l1="Multimedia_Elektronik",
        category_l2="Audio_Hifi",
    )

    reason = ScraperService._get_filter_reason(
        detail=detail,
        adsearch=_make_adsearch(),
        exclude_commercial=False,
        min_rating=0,
    )

    assert reason is not None
    assert "Kein Preis" in reason
