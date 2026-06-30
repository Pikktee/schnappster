"""Tests für PriceWatchService: Alarm-Logik, Preis-Check-Ablauf, Routen."""

from sqlmodel import Session, select

from app.models.notification import (
    NOTIFICATION_PRICE_BELOW_THRESHOLD,
    NOTIFICATION_PRICE_DROP,
    Notification,
)
from app.models.price_watch import PricePoint, PriceWatch
from app.services.price_watch import PriceWatchService, _evaluate_alarm
from tests.conftest import TEST_USER_ID

PRICE_HTML = '<html><body><span class="price">{price}</span></body></html>'
CSS_LOCATOR = {"strategy": "css", "selector": ".price"}


# --- Reine Alarm-Logik ---
def test_alarm_no_threshold_on_drop():
    assert _evaluate_alarm(None, 100.0, 90.0, False) == NOTIFICATION_PRICE_DROP


def test_alarm_no_threshold_no_alarm_on_rise():
    assert _evaluate_alarm(None, 100.0, 110.0, False) is None


def test_alarm_no_threshold_no_alarm_on_first_check():
    assert _evaluate_alarm(None, None, 100.0, True) is None


def test_alarm_threshold_crossed_downward():
    assert _evaluate_alarm(100.0, 110.0, 90.0, False) == NOTIFICATION_PRICE_BELOW_THRESHOLD


def test_alarm_threshold_not_reached():
    # Senkung, aber bleibt über der Schwelle -> kein Alarm
    assert _evaluate_alarm(50.0, 110.0, 90.0, False) is None


def test_alarm_threshold_initial_already_below():
    assert _evaluate_alarm(100.0, None, 80.0, True) == NOTIFICATION_PRICE_BELOW_THRESHOLD


def test_alarm_threshold_below_but_rising_no_spam():
    # unter Schwelle, aber Preis steigt -> kein erneuter Alarm
    assert _evaluate_alarm(100.0, 90.0, 95.0, False) is None


def test_alarm_threshold_further_drop_below():
    assert _evaluate_alarm(100.0, 90.0, 80.0, False) == NOTIFICATION_PRICE_BELOW_THRESHOLD


# --- check_watch Integration (frische Sessions wegen Verbindungsfreigabe) ---
def _make_watch(engine, **kwargs) -> int:
    defaults = dict(
        owner_id=TEST_USER_ID,
        name="Test",
        url="https://example.com/p",
        locator=CSS_LOCATOR,
        currency="EUR",
    )
    defaults.update(kwargs)
    with Session(engine) as setup:
        watch = PriceWatch(**defaults)
        setup.add(watch)
        setup.commit()
        setup.refresh(watch)
        return watch.id


def _run_check(engine, monkeypatch, watch_id: int, price_text: str):
    monkeypatch.setattr(
        "app.services.price_watch.fetch_page_with_status",
        lambda url: (200, PRICE_HTML.format(price=price_text)),
    )
    with Session(engine) as svc_session:
        watch = svc_session.get(PriceWatch, watch_id)
        return PriceWatchService(svc_session).check_watch(watch)


def test_check_watch_records_drop_and_notifies(engine, monkeypatch):
    watch_id = _make_watch(engine, last_price=100.0)
    result = _run_check(engine, monkeypatch, watch_id, "90,00 €")

    assert result.alarm_triggered is True
    assert result.new_price == 90.0
    with Session(engine) as check:
        updated = check.get(PriceWatch, watch_id)
        assert updated.last_price == 90.0
        points = check.exec(select(PricePoint).where(PricePoint.pricewatch_id == watch_id)).all()
        assert len(points) == 1
        notifs = check.exec(select(Notification).where(Notification.owner_id == TEST_USER_ID)).all()
        assert len(notifs) == 1
        assert "Preis gefallen" in notifs[0].title


def test_check_watch_no_change_no_point_no_alarm(engine, monkeypatch):
    watch_id = _make_watch(engine, last_price=50.0)
    result = _run_check(engine, monkeypatch, watch_id, "50,00 €")

    assert result.alarm_triggered is False
    with Session(engine) as check:
        points = check.exec(select(PricePoint).where(PricePoint.pricewatch_id == watch_id)).all()
        assert points == []
        assert check.exec(select(Notification)).all() == []


def test_check_watch_threshold_alarm(engine, monkeypatch):
    watch_id = _make_watch(engine, last_price=120.0, notify_threshold=100.0)
    result = _run_check(engine, monkeypatch, watch_id, "95,00 €")

    assert result.alarm_triggered is True
    with Session(engine) as check:
        notif = check.exec(select(Notification)).first()
        assert notif.type == NOTIFICATION_PRICE_BELOW_THRESHOLD
        assert "Zielpreis erreicht" in notif.title


def test_check_watch_extraction_failure_sets_error(engine, monkeypatch):
    watch_id = _make_watch(engine, last_price=10.0)
    monkeypatch.setattr(
        "app.services.price_watch.fetch_page_with_status",
        lambda url: (200, "<html><body>kein Preis</body></html>"),
    )
    with Session(engine) as svc:
        result = PriceWatchService(svc).check_watch(svc.get(PriceWatch, watch_id))
    assert result.status == "error"
    with Session(engine) as check:
        updated = check.get(PriceWatch, watch_id)
        assert updated.consecutive_failures == 1
        assert updated.last_error is not None


# --- Routen-Smoke-Tests ---
def test_create_and_list_price_watch(client, monkeypatch):
    payload = {
        "name": "Mein Produkt",
        "url": "https://example.com/p",
        "locator": {"strategy": "jsonld", "script_index": 0, "path": ["offers", "price"]},
        "currency": "EUR",
        "scrape_interval_minutes": 360,
        "notify_threshold": 100.0,
    }
    created = client.post("/price-watches/", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Mein Produkt"
    assert body["notify_threshold"] == 100.0

    listing = client.get("/price-watches/")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_create_rejects_invalid_url(client):
    response = client.post(
        "/price-watches/",
        json={"name": "X", "url": "not-a-url", "locator": {}},
    )
    assert response.status_code == 422


def test_create_rejects_too_short_interval(client):
    response = client.post(
        "/price-watches/",
        json={
            "name": "X",
            "url": "https://example.com",
            "locator": {},
            "scrape_interval_minutes": 5,
        },
    )
    assert response.status_code == 422


def test_preview_returns_candidates(client, monkeypatch):
    html = (
        '<html><head><script type="application/ld+json">'
        '{"offers":{"price":"19.99","priceCurrency":"EUR"}}'
        "</script><title>Demo</title></head></html>"
    )
    monkeypatch.setattr(
        "app.routes.api.price_watches.fetch_page_with_status",
        lambda url: (200, html),
    )
    response = client.post("/price-watches/preview", json={"url": "https://example.com/p"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Demo"
    assert any(c["value"] == 19.99 for c in data["candidates"])


def test_update_and_delete_price_watch(client, monkeypatch):
    payload = {
        "name": "Produkt",
        "url": "https://example.com/p",
        "locator": {"strategy": "css", "selector": ".price"},
    }
    watch_id = client.post("/price-watches/", json=payload).json()["id"]

    patched = client.patch(f"/price-watches/{watch_id}", json={"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    assert client.delete(f"/price-watches/{watch_id}").status_code == 204
    assert client.get(f"/price-watches/{watch_id}").status_code == 404
