"""API-Routen für In-App-Benachrichtigungen."""

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.db import SessionDep
from app.models.notification import NotificationMarkRead, NotificationRead
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationRead])
def list_notifications(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
):
    """Gibt die Benachrichtigungen des Nutzers zurück (neueste zuerst)."""
    return NotificationService(session).list_for_user(current_user.user_id, unread_only, limit)


@router.get("/unread-count")
def unread_count(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
) -> dict[str, int]:
    """Gibt die Anzahl ungelesener Benachrichtigungen zurück (für das Glocken-Badge)."""
    return {"count": NotificationService(session).unread_count(current_user.user_id)}


@router.post("/mark-read", status_code=204)
def mark_read(
    data: NotificationMarkRead,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Markiert die angegebenen Benachrichtigungen als gelesen."""
    NotificationService(session).mark_read(current_user.user_id, data.ids)


@router.post("/mark-all-read", status_code=204)
def mark_all_read(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Markiert alle Benachrichtigungen des Nutzers als gelesen."""
    NotificationService(session).mark_all_read(current_user.user_id)
