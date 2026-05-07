"""API-Routen für Scrape-Läufe."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete
from sqlmodel import col, select

from app.core.auth import CurrentUser, get_current_user, require_admin
from app.core.db import UserDbSession
from app.models.adsearch import AdSearch
from app.models.logs_scraperun import ScrapeRun, ScrapeRunRead

router = APIRouter(prefix="/scraperuns", tags=["ScrapeRuns"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[ScrapeRunRead])
def list_scraperuns(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    adsearch_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Gibt Scrape-Läufe zurück, optional nach adsearch_id gefiltert, nach started_at absteigend.

    Normale Nutzer sehen nur Läufe zu eigenen Suchaufträgen; Admins sehen alle (Logs/Übersicht).
    """
    if current_user.role == "admin":
        query = select(ScrapeRun).order_by(col(ScrapeRun.started_at).desc()).limit(limit)
        if adsearch_id is not None:
            query = query.where(ScrapeRun.adsearch_id == adsearch_id)
        runs = session.exec(query).all()
        result = [ScrapeRunRead.model_validate(run) for run in runs]
        session.rollback()
        return result

    query = (
        select(ScrapeRun)
        .join(AdSearch, col(ScrapeRun.adsearch_id) == col(AdSearch.id))
        .where(AdSearch.owner_id == current_user.user_id)
        .order_by(col(ScrapeRun.started_at).desc())
        .limit(limit)
    )
    if adsearch_id is not None:
        query = query.where(ScrapeRun.adsearch_id == adsearch_id)
    runs = session.exec(query).all()
    result = [ScrapeRunRead.model_validate(run) for run in runs]
    session.rollback()
    return result


@router.delete("/", status_code=204)
def clear_scraperuns(
    session: UserDbSession,
    _: CurrentUser = Depends(require_admin),  # noqa: B008
):
    """Löscht alle Scrape-Läufe."""
    session.execute(delete(ScrapeRun))
    session.commit()
