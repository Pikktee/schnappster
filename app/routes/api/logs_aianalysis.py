"""API-Routen für KI-Analyse-Logs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete
from sqlmodel import col, select

from app.core.auth import CurrentUser, require_admin
from app.core.db import UserDbSession
from app.models.logs_aianalysis import AIAnalysisLog, AIAnalysisLogRead

router = APIRouter(prefix="/aianalysislogs", tags=["AIAnalysisLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AIAnalysisLogRead])
def list_aianalysislogs(
    session: UserDbSession,
    adsearch_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt KI-Analyse-Logs zurück (nur erfolgreiche Analysen), neueste zuerst."""
    query = select(AIAnalysisLog).order_by(col(AIAnalysisLog.created_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(AIAnalysisLog.adsearch_id == adsearch_id)

    return session.exec(query).all()


@router.delete("/", status_code=204)
def clear_aianalysislogs(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Löscht alle KI-Analyse-Logs."""
    session.execute(delete(AIAnalysisLog))
    session.commit()
