"""API-Routen für Fehlerlogs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete
from sqlmodel import col, select

from app.core.auth import CurrentUser, require_admin
from app.core.db import UserDbSession
from app.models.logs_error import ErrorLog, ErrorLogRead

router = APIRouter(prefix="/errorlogs", tags=["ErrorLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[ErrorLogRead])
def list_errorlogs(
    session: UserDbSession,
    adsearch_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt Fehlerlogs zurück, optional nach adsearch_id gefiltert, neueste zuerst."""
    query = select(ErrorLog).order_by(col(ErrorLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(ErrorLog.adsearch_id == adsearch_id)

    return session.exec(query).all()


@router.delete("/", status_code=204)
def clear_errorlogs(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Löscht alle Fehlerlogs."""
    session.execute(delete(ErrorLog))
    session.commit()
