"""API-Routen für Fehlerlogs."""

from fastapi import APIRouter, Depends
from sqlmodel import col, select

from app.core.auth import CurrentUser, require_admin
from app.core.db import UserDbSession, api_async_session_maker, apply_api_statement_timeout_async
from app.models.logs_error import ErrorLog, ErrorLogRead

router = APIRouter(prefix="/errorlogs", tags=["ErrorLogs"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[ErrorLogRead])
async def list_errorlogs(
    adsearch_id: int | None = None,
    limit: int = 100,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Gibt Fehlerlogs zurück, optional nach adsearch_id gefiltert, neueste zuerst."""
    async with api_async_session_maker() as session:
        await apply_api_statement_timeout_async(session)
        query = select(ErrorLog).order_by(col(ErrorLog.created_at).desc()).limit(limit)

        if adsearch_id is not None:
            query = query.where(ErrorLog.adsearch_id == adsearch_id)

        res = await session.execute(query)
        rows = list(res.scalars().all())
        return [ErrorLogRead.model_validate(r) for r in rows]


@router.delete("/", status_code=204)
def clear_errorlogs(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Löscht alle Fehlerlogs."""
    for log in session.exec(select(ErrorLog)).all():
        session.delete(log)
    session.commit()
