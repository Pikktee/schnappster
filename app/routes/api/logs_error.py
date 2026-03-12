"""API-Routen für Fehlerlogs."""

from fastapi import APIRouter
from sqlmodel import col, select

from app.core.db import DbSession
from app.models.logs_error import ErrorLog, ErrorLogRead

router = APIRouter(prefix="/errorlogs", tags=["ErrorLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[ErrorLogRead])
def list_errorlogs(session: DbSession, adsearch_id: int | None = None, limit: int = 100):
    """Gibt Fehlerlogs zurück, optional nach adsearch_id gefiltert, neueste zuerst."""
    query = select(ErrorLog).order_by(col(ErrorLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(ErrorLog.adsearch_id == adsearch_id)

    return session.exec(query).all()


@router.delete("/", status_code=204)
def clear_errorlogs(session: DbSession):
    """Löscht alle Fehlerlogs."""
    for log in session.exec(select(ErrorLog)).all():
        session.delete(log)
    session.commit()
