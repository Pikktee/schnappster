"""Tests für den Deal-Alarm: MyDealz-Parser, DealWatchService (Baseline/Schwelle), API."""

import json
from unittest.mock import patch

from sqlmodel import select

from app.models.deal_watch import Deal, DealWatch
from app.scraper import mydealz
from app.services.deal_watch import DealWatchService
from app.services.notification import NotificationService

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _deal_node(
    thread_id: str,
    title: str,
    temperature: float,
    *,
    price: float = 0,
    merchant: str = "Amazon",
    type_: str = "Deal",
    expired: bool = False,
    main_image: dict | None = {"path": "threads/raw/h33IA", "name": "img_1"},  # noqa: B006
    published_at: int = 1782900000,
    hot_date: int = 0,
) -> str:
    """Baut einen data-vue3-Knoten wie auf der echten MyDealz-Seite."""
    thread = {
        "threadId": thread_id,
        "titleSlug": "deal-slug",
        "title": title,
        "temperature": temperature,
        "price": price,
        "nextBestPrice": 0,
        "merchant": {"merchantName": merchant},
        "type": type_,
        "isExpired": expired,
        "publishedAt": published_at,
        "hotDate": hot_date,
    }
    if main_image is not None:
        thread["mainImage"] = main_image
    payload = {"name": "ThreadMainListItemNormalizer", "props": {"thread": thread}}
    return f"<div data-vue3='{json.dumps(payload)}'></div>"


def _deals_html(nodes: list[str]) -> str:
    return "<html><body>" + "".join(nodes) + "</body></html>"


# --- Parser ---


def test_parse_deals_extracts_fields():
    """threadId/title/temperature/price/merchant + kanonische /deals/-URL werden geparst."""
    html = _deals_html(
        [_deal_node("2805228", "LEGO Creator", 161.62, price=12.99, merchant="Müller")]
    )
    deals = mydealz.parse_deals(html)
    assert len(deals) == 1
    d = deals[0]
    assert d.external_id == "2805228"
    assert d.title == "LEGO Creator"
    assert d.temperature == 161.62
    assert d.price == 12.99
    assert d.merchant == "Müller"
    assert d.url == "https://www.mydealz.de/deals/deal-slug-2805228"


def test_parse_deals_skips_expired_and_non_deals():
    """Abgelaufene Deals und Nicht-Deal-Typen (z. B. Diskussionen) werden übersprungen."""
    html = _deals_html(
        [
            _deal_node("1", "Aktiv", 200),
            _deal_node("2", "Abgelaufen", 300, expired=True),
            _deal_node("3", "Diskussion", 50, type_="Discussion"),
        ]
    )
    deals = mydealz.parse_deals(html)
    assert [d.external_id for d in deals] == ["1"]


def test_parse_deals_zero_price_becomes_none():
    """MyDealz nutzt 0 für 'kein Preis' → wird als None geparst."""
    deals = mydealz.parse_deals(_deals_html([_deal_node("9", "Gratis", 100, price=0)]))
    assert deals[0].price is None


def test_parse_deals_builds_image_url_from_main_image():
    """Aus mainImage (path + name) wird die CDN-Thumbnail-URL gebaut."""
    deals = mydealz.parse_deals(_deals_html([_deal_node("5", "Mit Bild", 100)]))
    assert deals[0].image_url == (
        "https://static.mydealz.de/threads/raw/h33IA/img_1/re/768x768/qt/60/img_1.jpg"
    )


def test_parse_deals_without_image_yields_none():
    """Ohne mainImage bleibt image_url None (Karte zeigt den Platzhalter)."""
    deals = mydealz.parse_deals(_deals_html([_deal_node("6", "Ohne Bild", 100, main_image=None)]))
    assert deals[0].image_url is None


def test_parse_deals_extracts_hot_date_and_published_at():
    """hotDate/publishedAt werden übernommen (Basis für die Zeit bis heiß)."""
    node = _deal_node("7", "Aufsteiger", 250, published_at=1782900000, hot_date=1782903600)
    deal = mydealz.parse_deals(_deals_html([node]))[0]
    assert deal.published_at == 1782900000
    assert deal.hot_date == 1782903600  # 1 Stunde bis heiß


def test_parse_deals_hot_date_zero_becomes_none():
    """MyDealz nutzt hotDate 0 für 'noch nicht heiß' → wird als None geparst."""
    deal = mydealz.parse_deals(_deals_html([_deal_node("8", "Neu", 90, hot_date=0)]))[0]
    assert deal.hot_date is None


def test_build_search_url_encodes_query():
    assert mydealz.build_search_url("lego star wars") == (
        "https://www.mydealz.de/search?q=lego+star+wars"
    )


# --- Service: Baseline + Schwelle + Benachrichtigung ---


def _make_watch(session, *, min_temperature=None):
    watch = DealWatch(
        owner_id=TEST_USER_ID,
        name="LEGO",
        query="lego",
        min_temperature=min_temperature,
        is_active=True,
    )
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return watch


def test_first_check_is_silent_baseline(session):
    """Erster Check speichert vorhandene Deals, benachrichtigt aber nicht (Baseline)."""
    watch = _make_watch(session)
    watch_id = watch.id  # vor dem Check festhalten (Service schließt die Session)
    html = _deals_html([_deal_node("1", "A", 500), _deal_node("2", "B", 120)])
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(200, html)):
        result = DealWatchService(session).check_watch(watch)

    assert result.alarms == 0
    saved = session.exec(select(Deal).where(Deal.deal_watch_id == watch_id)).all()
    assert len(saved) == 2
    assert all(not d.notified for d in saved)
    assert NotificationService(session).unread_count(TEST_USER_ID) == 0


def test_new_hot_deal_notifies_after_baseline(session):
    """Nach der Baseline löst ein neuer Deal über der Schwelle einen Alarm aus."""
    watch = _make_watch(session, min_temperature=300)
    watch_id = watch.id
    baseline = _deals_html([_deal_node("1", "A", 500)])
    later = _deals_html([_deal_node("1", "A", 500), _deal_node("2", "Neu heiß", 600, price=9.99)])

    service = DealWatchService(session)
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(200, baseline)):
        service.check_watch(watch)
    reloaded = session.get(DealWatch, watch_id)  # last_checked_at ist jetzt gesetzt
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(200, later)):
        result = service.check_watch(reloaded)

    assert result.alarms == 1
    new_deal = session.exec(select(Deal).where(Deal.external_id == "2")).first()
    assert new_deal is not None and new_deal.notified is True
    assert NotificationService(session).unread_count(TEST_USER_ID) == 1


def test_new_deal_below_threshold_saved_but_not_notified(session):
    """Ein neuer Deal unter der Schwelle wird gespeichert, aber löst keinen Alarm aus."""
    watch = _make_watch(session, min_temperature=300)
    watch_id = watch.id
    baseline = _deals_html([_deal_node("1", "A", 500)])
    later = _deals_html([_deal_node("1", "A", 500), _deal_node("2", "Lauwarm", 150)])

    service = DealWatchService(session)
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(200, baseline)):
        service.check_watch(watch)
    reloaded = session.get(DealWatch, watch_id)
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(200, later)):
        result = service.check_watch(reloaded)

    assert result.alarms == 0
    lukewarm = session.exec(select(Deal).where(Deal.external_id == "2")).first()
    assert lukewarm is not None and lukewarm.notified is False
    assert NotificationService(session).unread_count(TEST_USER_ID) == 0


def test_check_records_error_when_blocked(session):
    """Blockade/kein brauchbares HTML → last_error gesetzt, keine Exception."""
    watch = _make_watch(session)
    watch_id = watch.id
    with patch("app.services.deal_watch.mydealz.fetch_deals_html", return_value=(503, "")):
        result = DealWatchService(session).check_watch(watch)
    assert result.status == "error"
    reloaded = session.get(DealWatch, watch_id)
    assert reloaded.last_error is not None and reloaded.consecutive_failures == 1


# --- API ---


def test_create_deal_watch(client):
    """POST /deal-watches/ legt einen Alarm an; Name aus Suchbegriff abgeleitet."""
    response = client.post(
        "/deal-watches/", json={"query": "lego millennium falcon", "min_temperature": 300}
    )
    assert response.status_code == 201
    result = response.json()
    assert result["query"] == "lego millennium falcon"
    assert result["name"] == "lego millennium falcon"
    assert result["source"] == "mydealz"
    assert result["min_temperature"] == 300


def test_create_deal_watch_rejects_empty_query(client):
    """POST ohne Suchbegriff wird mit 422 abgelehnt."""
    assert client.post("/deal-watches/", json={"query": "   "}).status_code == 422


def test_preview_deal_watch(client):
    """POST /deal-watches/preview liefert die aktuell gefundenen Deals (gemockter Abruf)."""
    html = _deals_html([_deal_node("1", "LEGO Deal", 420, price=19.99)])
    with patch(
        "app.routes.api.deal_watches.mydealz.fetch_deals_html", return_value=(200, html)
    ):
        response = client.post("/deal-watches/preview", json={"query": "lego"})
    assert response.status_code == 200
    deals = response.json()["deals"]
    assert len(deals) == 1
    assert deals[0]["temperature"] == 420
    assert deals[0]["merchant"] == "Amazon"


def test_list_and_get_deals_for_watch(client, session):
    """Angelegter Deal + GET /deal-watches/{id}/deals liefert ihn zurück."""
    watch = _make_watch(session)
    session.add(
        Deal(
            owner_id=TEST_USER_ID,
            deal_watch_id=watch.id,
            external_id="42",
            title="Testdeal",
            url="https://www.mydealz.de/deals/x-42",
            temperature=333.0,
        )
    )
    session.commit()

    response = client.get(f"/deal-watches/{watch.id}/deals")
    assert response.status_code == 200
    deals = response.json()
    assert len(deals) == 1 and deals[0]["external_id"] == "42"


def test_deals_sorted_by_time_to_hot(client, session):
    """Schnellste Aufsteiger (kleinste Zeit bis heiß) zuerst; ohne hot_date danach."""
    watch = _make_watch(session)
    rows = [
        # (external_id, temperature, published_at, hot_date)
        ("slow", 200.0, 1000, 1000 + 7200),  # 2 h bis heiß
        ("fast", 300.0, 1000, 1000 + 1800),  # 0,5 h bis heiß → zuerst
        ("hottest", 900.0, 1000, 0),  # nie heiß geworden → trotz Top-Temp ans Ende
    ]
    for ext, temp, pub, hot in rows:
        session.add(
            Deal(
                owner_id=TEST_USER_ID,
                deal_watch_id=watch.id,
                external_id=ext,
                title=ext,
                url=f"https://www.mydealz.de/deals/x-{ext}",
                temperature=temp,
                published_at=pub,
                hot_date=hot or None,
            )
        )
    session.commit()

    deals = client.get(f"/deal-watches/{watch.id}/deals").json()
    assert [d["external_id"] for d in deals] == ["fast", "slow", "hottest"]
