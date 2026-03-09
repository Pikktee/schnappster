from fastapi import APIRouter
from sqlmodel import col, select

from app.core.db import DbSession
from app.models.scraperun import ScrapeRun, ScrapeRunRead

router = APIRouter(prefix="/scraperuns", tags=["ScrapeRuns"])


# --------------
# --- Routes ---
# --------------
@router.get("/", response_model=list[ScrapeRunRead])
def list_scraperuns(session: DbSession, adsearch_id: int | None = None, limit: int = 50):
    """
    Returns all scrape runs.
    """
    query = select(ScrapeRun).order_by(col(ScrapeRun.started_at).desc()).limit(limit)

    if adsearch_id is not None:
        query = query.where(ScrapeRun.adsearch_id == adsearch_id)

    return session.exec(query).all()
