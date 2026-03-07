from fastapi import APIRouter
from sqlmodel import col, select

from app.core.db import DbSession
from app.models.errorlog import ErrorLog, ErrorLogRead

router = APIRouter(prefix="/errorlogs", tags=["ErrorLogs"])


@router.get("/", response_model=list[ErrorLogRead])
def list_errorlogs(session: DbSession, adsearch_id: int | None = None, limit: int = 100):
    """
    Returns all error logs.
    """
    query = select(ErrorLog).order_by(col(ErrorLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(ErrorLog.adsearch_id == adsearch_id)

    return session.exec(query).all()
