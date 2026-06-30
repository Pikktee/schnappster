"""Service für persistente In-App-Benachrichtigungen."""

import logging

from sqlalchemy import update
from sqlmodel import Session, col, desc, func, select

from app.models.notification import Notification

logger = logging.getLogger(__name__)

MAX_NOTIFICATIONS = 100


class NotificationService:
    """Liest und schreibt In-App-Benachrichtigungen eines Benutzers."""

    def __init__(self, session: Session):
        """Erstellt den Service mit der übergebenen Datenbank-Session."""
        self.session = session

    def create(
        self,
        owner_id: str,
        type: str,
        title: str,
        body: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """Legt eine Benachrichtigung an und gibt sie zurück."""
        notification = Notification(owner_id=owner_id, type=type, title=title, body=body, link=link)
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def list_for_user(
        self, owner_id: str, unread_only: bool = False, limit: int = MAX_NOTIFICATIONS
    ) -> list[Notification]:
        """Gibt Benachrichtigungen (neueste zuerst) zurück."""
        query = select(Notification).where(Notification.owner_id == owner_id)
        if unread_only:
            query = query.where(col(Notification.is_read).is_(False))
        query = query.order_by(desc(Notification.created_at)).limit(limit)
        return list(self.session.exec(query).all())

    def unread_count(self, owner_id: str) -> int:
        """Anzahl ungelesener Benachrichtigungen."""
        return self.session.exec(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.owner_id == owner_id,
                col(Notification.is_read).is_(False),
            )
        ).one()

    def mark_read(self, owner_id: str, ids: list[int]) -> int:
        """Markiert die angegebenen Benachrichtigungen des Nutzers als gelesen."""
        if not ids:
            return 0
        result = self.session.execute(
            update(Notification)
            .where(
                col(Notification.owner_id) == owner_id,
                col(Notification.id).in_(ids),
            )
            .values(is_read=True)
        )
        self.session.commit()
        return result.rowcount or 0

    def mark_all_read(self, owner_id: str) -> int:
        """Markiert alle Benachrichtigungen des Nutzers als gelesen."""
        result = self.session.execute(
            update(Notification)
            .where(
                col(Notification.owner_id) == owner_id,
                col(Notification.is_read).is_(False),
            )
            .values(is_read=True)
        )
        self.session.commit()
        return result.rowcount or 0
