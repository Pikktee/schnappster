"""API-Routen für KI-Analyse-Logs."""

from fastapi import APIRouter, Depends
from sqlmodel import col, select

from app.core.auth import CurrentUser, require_admin
from app.core.db import UserDbSession, api_async_session_maker, apply_api_statement_timeout_async
from app.models.logs_aianalysis import AIAnalysisLog, AIAnalysisLogRead

router = APIRouter(prefix="/aianalysislogs", tags=["AIAnalysisLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AIAnalysisLogRead])
async def list_aianalysislogs(
    adsearch_id: int | None = None,
    limit: int = 100,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt KI-Analyse-Logs zurück (nur erfolgreiche Analysen), neueste zuerst."""
    async with api_async_session_maker() as session:
        await apply_api_statement_timeout_async(session)
        query = select(AIAnalysisLog).order_by(col(AIAnalysisLog.created_at).desc()).limit(limit)

        if adsearch_id is not None:
            query = query.where(AIAnalysisLog.adsearch_id == adsearch_id)

        res = await session.execute(query)
        rows = list(res.scalars().all())
        return [AIAnalysisLogRead.model_validate(r) for r in rows]


@router.delete("/", status_code=204)
def clear_aianalysislogs(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Löscht alle KI-Analyse-Logs."""
    for log in session.exec(select(AIAnalysisLog)).all():
        session.delete(log)
    session.commit()
