"""Tests für den Ergebnis-Stream (/feed/): Mischung, Chronologie, Filter."""

from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.deal_watch import Deal, DealWatch
from app.models.price_watch import PricePoint, PriceWatch
from app.models.search_order import SearchOrder

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _seed_mixed(session):
    """Ein Ad (vor 2 h), ein Deal (vor 1 h veröffentlicht), eine Preisänderung (jetzt)."""
    now = datetime.now(UTC)
    order = SearchOrder(owner_id=TEST_USER_ID, name="lego", query="lego")
    session.add(order)
    session.flush()
    search = AdSearch(
        owner_id=TEST_USER_ID,
        search_order_id=order.id,
        name="lego",
        url="https://www.kleinanzeigen.de/s-lego/k0",
    )
    watch = DealWatch(
        owner_id=TEST_USER_ID, search_order_id=order.id, name="lego", query="lego"
    )
    price_watch = PriceWatch(
        owner_id=TEST_USER_ID, name="Konsole", url="https://shop.example/x"
    )
    session.add_all([search, watch, price_watch])
    session.flush()

    session.add(
        Ad(
            owner_id=TEST_USER_ID,
            adsearch_id=search.id,
            external_id="a1",
            title="Anzeige",
            url="https://www.kleinanzeigen.de/s-anzeige/x/1",
            price=80,
            bargain_score=9,
            is_analyzed=True,
            first_seen_at=now - timedelta(hours=2),
        )
    )
    session.add(
        Deal(
            owner_id=TEST_USER_ID,
            deal_watch_id=watch.id,
            external_id="d1",
            title="Deal",
            url="https://www.mydealz.de/deals/x-1",
            price=120,
            published_at=int((now - timedelta(hours=1)).timestamp()),
        )
    )
    session.add(
        PricePoint(
            owner_id=TEST_USER_ID,
            pricewatch_id=price_watch.id,
            price=199.0,
            recorded_at=now,
        )
    )
    session.commit()
    return order


def test_feed_mixes_sources_chronologically(client, session):
    """Alle drei Quellen erscheinen gemischt, neueste zuerst."""
    _seed_mixed(session)
    body = client.get("/feed/").json()
    assert body["total"] == 3
    assert [item["type"] for item in body["items"]] == ["price", "deal", "ad"]


def test_feed_filters_by_source(client, session):
    """source=mydealz liefert nur Deals."""
    _seed_mixed(session)
    body = client.get("/feed/?source=mydealz").json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "deal"


def test_feed_min_score_returns_only_ads(client, session):
    """Ein Mindest-Score blendet Deals/Preis-Ereignisse aus (nur Anzeigen haben einen Score)."""
    _seed_mixed(session)
    body = client.get("/feed/?min_score=8").json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "ad"
    assert body["items"][0]["ad"]["bargain_score"] == 9


def test_feed_filters_by_search_order(client, session):
    """search_order_id begrenzt auf die Funde dieses Auftrags (ohne Preis-Ereignisse)."""
    order = _seed_mixed(session)
    body = client.get(f"/feed/?search_order_id={order.id}").json()
    assert body["total"] == 2
    assert {item["type"] for item in body["items"]} == {"ad", "deal"}


def test_feed_price_event_carries_previous_price(client, session):
    """Die zweite Preisänderung kennt den vorherigen Preis (für die Richtungsanzeige)."""
    _seed_mixed(session)
    watch_id = session.exec(select(PriceWatch.id)).first()
    session.add(
        PricePoint(owner_id=TEST_USER_ID, pricewatch_id=watch_id, price=149.0)
    )
    session.commit()

    body = client.get("/feed/?source=price").json()
    newest = body["items"][0]["price_event"]
    assert newest["price"] == 149.0
    assert newest["previous_price"] == 199.0
