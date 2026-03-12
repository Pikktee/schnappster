"""API-Routen für KI-Analyse-Logs."""

from fastapi import APIRouter
from sqlmodel import col, select

from app.core.db import DbSession
from app.models.logs_aianalysis import AIAnalysisLog, AIAnalysisLogRead

router = APIRouter(prefix="/aianalysislogs", tags=["AIAnalysisLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AIAnalysisLogRead])
def list_aianalysislogs(session: DbSession, adsearch_id: int | None = None, limit: int = 100):
    """Gibt KI-Analyse-Logs zurück (nur erfolgreiche Analysen), neueste zuerst."""
    query = select(AIAnalysisLog).order_by(col(AIAnalysisLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(AIAnalysisLog.adsearch_id == adsearch_id)

    return session.exec(query).all()


@router.delete("/", status_code=204)
def clear_aianalysislogs(session: DbSession):
    """Löscht alle KI-Analyse-Logs."""
    for log in session.exec(select(AIAnalysisLog)).all():
        session.delete(log)
    session.commit()
