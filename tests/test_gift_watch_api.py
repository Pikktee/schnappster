"""Integrationstests für die Fundgrube-Routen (GiftWatch ↔ AdSearch-Kind)."""

import pytest

from app.core.background_jobs import get_background_jobs
from app.models.adsearch import AdSearch


class _NoopJobs:
    """Ersetzt den Scheduler im Test (kein echtes Job-Queuing)."""

    def trigger_scrape_once(self) -> None:
        pass


@pytest.fixture(name="gclient")
def gclient_fixture(client):
    """Test-Client mit deaktiviertem Hintergrund-Scheduler."""
    client.app.dependency_overrides[get_background_jobs] = lambda: _NoopJobs()
    return client


def _create(gclient, **overrides) -> dict:
    payload = {
        "postal_code": "50667",
        "radius_km": 10,
        "interest_profile": "Werkzeug, Vintage-HiFi, Massivholz",
        "focus_keywords": "bosch, makita",
        "exclude_keywords": "kinderkleidung",
        "vehicle": "estate",
        "can_carry_heavy": True,
    }
    payload.update(overrides)
    resp = gclient.post("/gift-watches/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_builds_gift_adsearch_child(gclient, session):
    data = _create(gclient)
    assert data["postal_code"] == "50667"
    assert data["vehicle"] == "estate"
    assert data["can_carry_heavy"] is True
    assert data["adsearch_id"] is not None

    child = session.get(AdSearch, data["adsearch_id"])
    assert child is not None
    assert child.gift_watch_id == data["id"]
    assert "zu-verschenken-tauschen" in child.url
    assert "locationStr=50667" in child.url
    assert "radiusKm=10" in child.url
    # exclude_keywords/-categories werden auf das Kind gespiegelt (Gratis-Filter).
    assert child.blacklist_keywords == "kinderkleidung"


def test_default_name_from_postal_code(gclient):
    data = _create(gclient, name="")
    assert "50667" in data["name"]


def test_gift_child_not_adopted_by_search_orders(gclient):
    _create(gclient)
    # Die Gift-AdSearch darf NICHT als verwaister Suchauftrag adoptiert werden.
    resp = gclient.get("/search-orders/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_get_delete_roundtrip(gclient, session):
    created = _create(gclient)
    watch_id = created["id"]
    adsearch_id = created["adsearch_id"]

    listed = gclient.get("/gift-watches/").json()
    assert len(listed) == 1

    got = gclient.get(f"/gift-watches/{watch_id}")
    assert got.status_code == 200

    deleted = gclient.delete(f"/gift-watches/{watch_id}")
    assert deleted.status_code == 204
    assert gclient.get("/gift-watches/").json() == []
    # Kind ebenfalls entfernt.
    assert session.get(AdSearch, adsearch_id) is None


def test_update_resyncs_adsearch_url(gclient, session):
    created = _create(gclient, radius_km=5)
    resp = gclient.patch(f"/gift-watches/{created['id']}", json={"radius_km": 25})
    assert resp.status_code == 200

    child = session.get(AdSearch, created["adsearch_id"])
    session.refresh(child)
    assert "radiusKm=25" in child.url
    assert child.radius_km == 25


def test_invalid_postal_code_rejected(gclient):
    resp = gclient.post("/gift-watches/", json={"postal_code": "abc"})
    assert resp.status_code == 422


def test_invalid_vehicle_rejected(gclient):
    resp = gclient.post("/gift-watches/", json={"postal_code": "50667", "vehicle": "spaceship"})
    assert resp.status_code == 422
