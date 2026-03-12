"""AI analysis log API routes."""

from fastapi import APIRouter
from sqlmodel import col, select

from app.core.db import DbSession
from app.models.aianalysislog import AIAnalysisLog, AIAnalysisLogRead

router = APIRouter(prefix="/aianalysislogs", tags=["AIAnalysisLogs"])


# --------------
# --- Routes ---
# --------------
@router.get("/", response_model=list[AIAnalysisLogRead])
def list_aianalysislogs(session: DbSession, adsearch_id: int | None = None, limit: int = 100):
    """Return AI analysis logs (successful analyses only), newest first."""
    query = select(AIAnalysisLog).order_by(col(AIAnalysisLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(AIAnalysisLog.adsearch_id == adsearch_id)

    return session.exec(query).all()


@router.delete("/", status_code=204)
def clear_aianalysislogs(session: DbSession):
    """Delete all AI analysis logs."""
    for log in session.exec(select(AIAnalysisLog)).all():
        session.delete(log)
    session.commit()
