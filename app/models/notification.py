"""Generisches In-App-Benachrichtigungsmodell und API-Schemas."""

from datetime import UTC, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

# Bekannte Benachrichtigungstypen (frei erweiterbar).
NOTIFICATION_PRICE_DROP = "price_drop"
NOTIFICATION_PRICE_BELOW_THRESHOLD = "price_below_threshold"


class Notification(SQLModel, table=True):
    """Eine persistente In-App-Benachrichtigung für einen Benutzer."""

    __tablename__ = "notifications"  # type: ignore
    __table_args__ = (
        Index("idx_notifications_owner_read_created", "owner_id", "is_read", "created_at"),
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    type: str
    title: str
    body: str | None = None
    # In-App-Ziel beim Klick (z.B. "/price-alerts/12").
    link: str | None = None
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class NotificationRead(SQLModel):
    """API-Ausgabe für eine Benachrichtigung."""

    id: int
    type: str
    title: str
    body: str | None
    link: str | None
    is_read: bool
    created_at: datetime


class NotificationMarkRead(SQLModel):
    """API-Eingabe zum Markieren bestimmter Benachrichtigungen als gelesen."""

    ids: list[int]
