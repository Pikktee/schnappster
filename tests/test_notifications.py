"""Tests für den NotificationService und die Benachrichtigungs-Routen."""

from sqlmodel import select

from app.models.notification import Notification
from app.services.notification import NotificationService
from tests.conftest import TEST_USER_ID


def test_notification_create_and_unread_count(session):
    service = NotificationService(session)
    service.create("user-a", "price_drop", "Titel", "Body", "/price-alerts/1")
    assert service.unread_count("user-a") == 1
    items = service.list_for_user("user-a")
    assert len(items) == 1 and items[0].title == "Titel"


def test_notification_mark_read(session):
    service = NotificationService(session)
    created = service.create("user-a", "price_drop", "Titel")
    service.mark_read("user-a", [created.id])
    assert service.unread_count("user-a") == 0


def test_notification_owner_isolation(session):
    service = NotificationService(session)
    service.create("user-a", "price_drop", "A")
    b_notif = service.create("user-b", "price_drop", "B")
    # user-a darf user-b's Benachrichtigung nicht als gelesen markieren
    service.mark_read("user-a", [b_notif.id])
    assert service.unread_count("user-b") == 1
    assert len(service.list_for_user("user-a")) == 1


def test_notification_unread_only_filter(session):
    service = NotificationService(session)
    first = service.create("user-a", "x", "1")
    service.create("user-a", "x", "2")
    service.mark_read("user-a", [first.id])
    assert len(service.list_for_user("user-a", unread_only=True)) == 1
    assert len(service.list_for_user("user-a", unread_only=False)) == 2


def test_mark_all_read(session):
    service = NotificationService(session)
    service.create("user-a", "x", "1")
    service.create("user-a", "x", "2")
    assert service.mark_all_read("user-a") == 2
    assert service.unread_count("user-a") == 0


# --- Routen ---
def test_notifications_routes(client, session):
    NotificationService(session).create(
        TEST_USER_ID, "price_drop", "Test", "Body", "/price-alerts/1"
    )

    listing = client.get("/notifications/")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    assert client.get("/notifications/unread-count").json()["count"] == 1

    assert client.post("/notifications/mark-all-read").status_code == 204
    assert client.get("/notifications/unread-count").json()["count"] == 0


def test_notifications_route_owner_scoped(client, session):
    # Benachrichtigung eines anderen Nutzers ist nicht sichtbar
    NotificationService(session).create("someone-else", "price_drop", "Fremd")
    assert client.get("/notifications/").json() == []
    remaining = session.exec(select(Notification)).all()
    assert len(remaining) == 1  # existiert noch, nur nicht für diesen Nutzer
