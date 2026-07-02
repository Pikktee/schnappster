"""Tests für vereinheitlichte Suchaufträge: Kinder-Sync, Adoption, Kaskaden-Löschen."""

from sqlmodel import select

from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.deal_watch import Deal, DealWatch
from app.models.search_order import SearchOrder

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _create_payload(**overrides):
    payload = {
        "query": "lego millennium falcon",
        "scrape_interval_minutes": 30,
        "use_kleinanzeigen": True,
        "use_ebay": True,
        "use_mydealz": True,
        "postal_code": "50667",
        "radius_km": 25,
        "min_price": 50,
        "max_price": 400,
        "mydealz_max_price": 600,
        "mydealz_min_temperature": 200,
    }
    payload.update(overrides)
    return payload


def test_create_order_spawns_children(client, session):
    """Create legt Eltern + je gewählter Quelle ein Kind mit korrekter Konfiguration an."""
    response = client.post("/search-orders/", json=_create_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "lego millennium falcon"
    assert body["kleinanzeigen"] is not None
    assert body["ebay"] is not None
    assert body["mydealz"] is not None

    ka = body["kleinanzeigen"]
    assert ka["platform"] == "kleinanzeigen"
    assert ka["postal_code"] == "50667" and ka["radius_km"] == 25
    assert ka["min_price"] == 50 and ka["max_price"] == 400
    assert "lego" in ka["url"]

    ebay = body["ebay"]
    assert ebay["platform"] == "ebay"
    assert ebay["postal_code"] is None  # eBay ist bundesweit
    assert "ebay" in ebay["url"]

    mydealz = body["mydealz"]
    assert mydealz["max_price"] == 600
    assert mydealz["min_temperature"] == 200


def test_create_requires_a_source(client):
    """Ohne gewählte Quelle wird das Anlegen abgelehnt."""
    payload = _create_payload(use_kleinanzeigen=False, use_ebay=False, use_mydealz=False)
    assert client.post("/search-orders/", json=payload).status_code == 422


def test_mydealz_interval_clamped_to_minimum(client):
    """Ein 5-Minuten-Intervall wird für das MyDealz-Kind auf das Deal-Minimum angehoben."""
    payload = _create_payload(scrape_interval_minutes=5, use_ebay=False)
    body = client.post("/search-orders/", json=payload).json()
    assert body["kleinanzeigen"]["scrape_interval_minutes"] == 5
    assert body["mydealz"]["scrape_interval_minutes"] == 15


def test_patch_toggles_sources(client, session):
    """Abwählen entfernt Kind + Funde; Anwählen legt ein neues Kind an."""
    order_id = client.post("/search-orders/", json=_create_payload(use_mydealz=False)).json()["id"]
    ebay_child = session.exec(
        select(AdSearch).where(AdSearch.search_order_id == order_id, AdSearch.platform == "ebay")
    ).first()
    session.add(
        Ad(
            owner_id=TEST_USER_ID,
            adsearch_id=ebay_child.id,
            external_id="e1",
            title="Fund",
            url="https://www.ebay.de/itm/1",
        )
    )
    session.commit()

    response = client.patch(
        f"/search-orders/{order_id}", json={"use_ebay": False, "use_mydealz": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ebay"] is None
    assert body["mydealz"] is not None
    session.expire_all()
    assert session.exec(select(Ad).where(Ad.adsearch_id == ebay_child.id)).all() == []


def test_patch_query_updates_children(client, session):
    """Eine Suchbegriff-Änderung schreibt search_query/url/query auf alle Kinder durch."""
    order_id = client.post("/search-orders/", json=_create_payload()).json()["id"]
    body = client.patch(f"/search-orders/{order_id}", json={"query": "nintendo switch"}).json()
    assert body["query"] == "nintendo switch"
    assert body["kleinanzeigen"]["search_query"] == "nintendo switch"
    assert "nintendo" in body["kleinanzeigen"]["url"]
    assert body["mydealz"]["query"] == "nintendo switch"


def test_patch_is_active_propagates(client, session):
    """Pausieren schreibt is_active auf alle Kinder durch (Pipelines filtern auf Kind-Ebene)."""
    order_id = client.post("/search-orders/", json=_create_payload()).json()["id"]
    body = client.patch(f"/search-orders/{order_id}", json={"is_active": False}).json()
    assert body["is_active"] is False
    assert body["kleinanzeigen"]["is_active"] is False
    assert body["ebay"]["is_active"] is False
    assert body["mydealz"]["is_active"] is False


def test_delete_cascades_children_and_finds(client, session):
    """Löschen entfernt Eltern, Kinder und alle Funde."""
    order_id = client.post("/search-orders/", json=_create_payload()).json()["id"]
    watch = session.exec(select(DealWatch).where(DealWatch.search_order_id == order_id)).first()
    session.add(
        Deal(
            owner_id=TEST_USER_ID,
            deal_watch_id=watch.id,
            external_id="d1",
            title="Deal",
            url="https://www.mydealz.de/deals/x-1",
        )
    )
    session.commit()

    assert client.delete(f"/search-orders/{order_id}").status_code == 204
    session.expire_all()
    assert session.get(SearchOrder, order_id) is None
    assert session.exec(select(AdSearch).where(AdSearch.search_order_id == order_id)).all() == []
    assert session.exec(select(Deal).where(Deal.deal_watch_id == watch.id)).all() == []


def test_list_serializes_children(client):
    """Auch der Listen-Endpoint liefert die Quellen-Kinder (nicht nur das Detail)."""
    client.post("/search-orders/", json=_create_payload())
    orders = client.get("/search-orders/").json()
    assert orders[0]["kleinanzeigen"] is not None
    assert orders[0]["ebay"] is not None
    assert orders[0]["mydealz"] is not None


def test_read_carries_per_source_ad_counts(client, session):
    """Die Kinder tragen ihre eigenen Fund-Zähler; die Summe bleibt ad_count."""
    order_id = client.post("/search-orders/", json=_create_payload()).json()["id"]
    ka = session.exec(
        select(AdSearch).where(
            AdSearch.search_order_id == order_id, AdSearch.platform == "kleinanzeigen"
        )
    ).first()
    for i in range(2):
        session.add(
            Ad(
                owner_id=TEST_USER_ID,
                adsearch_id=ka.id,
                external_id=f"k{i}",
                title="Fund",
                url=f"https://www.kleinanzeigen.de/s-anzeige/x/{i}",
            )
        )
    session.commit()

    body = client.get(f"/search-orders/{order_id}").json()
    assert body["kleinanzeigen"]["ad_count"] == 2
    assert body["ebay"]["ad_count"] == 0
    assert body["ad_count"] == 2


def test_orphans_are_adopted_on_list(client, session):
    """Alt-/Extension-Suchen ohne Eltern bekommen beim Listen-Abruf einen Suchauftrag."""
    session.add(
        AdSearch(
            owner_id=TEST_USER_ID,
            name="Alte URL-Suche",
            url="https://www.kleinanzeigen.de/s-lego/k0",
        )
    )
    session.add(DealWatch(owner_id=TEST_USER_ID, name="Alter Alarm", query="lego"))
    session.commit()

    orders = client.get("/search-orders/").json()
    names = {o["name"] for o in orders}
    assert {"Alte URL-Suche", "Alter Alarm"} <= names
    adopted_watch = next(o for o in orders if o["name"] == "Alter Alarm")
    assert adopted_watch["mydealz"] is not None
    assert adopted_watch["query"] == "lego"
