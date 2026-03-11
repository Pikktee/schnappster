"""Ad search (Suchauftrag) API routes."""

import logging
import threading
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import DbSession, db_engine
from app.models.ad import Ad
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate
from app.models.errorlog import ErrorLog
from app.models.scraperun import ScrapeRun
from app.scraper.httpclient import fetch_page_checked
from app.scraper.parser import parse_search_title
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


# --------------
# --- Routes ---
# --------------
@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: DbSession):
    """Return all ad searches (Suchaufträge)."""
    return session.exec(select(AdSearch)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(adsearch_id: int, session: DbSession):
    """Return a specific ad search by ID; raise 404 if not found."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    return adsearch


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(
    data: AdSearchCreate,
    session: DbSession,
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Create a new ad search; URL is validated by fetch, name from page title if empty."""
    name = data.name.strip()
    title_from_page = _validate_search_url_reachable(data.url)

    if not name:
        if not title_from_page:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Kein Seitentitel auf der Seite gefunden. Bitte URL prüfen "
                    "oder einen Namen manuell eingeben."
                ),
            )
        name = title_from_page

    adsearch = AdSearch.model_validate({**data.model_dump(), "name": name})

    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)

    background_jobs.trigger_scrape_once()

    return adsearch


@router.patch("/{adsearch_id}", response_model=AdSearchRead)
def update_adsearch(adsearch_id: int, data: AdSearchUpdate, session: DbSession):
    """Update an existing ad search. URL cannot be changed after create; raise 404 if not found."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)

    # If client cleared the name, fetch current URL and use its title as new name.
    title_from_page: str | None = None
    if (
        "name" in update_data
        and isinstance(update_data["name"], str)
        and not update_data["name"].strip()
    ):
        title_from_page = _validate_search_url_reachable(adsearch.url)

    if (
        "name" in update_data
        and isinstance(update_data["name"], str)
        and not update_data["name"].strip()
    ):
        if not title_from_page:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Kein Seitentitel auf der Seite gefunden. Bitte URL prüfen "
                    "oder einen Namen manuell eingeben."
                ),
            )
        update_data["name"] = title_from_page

    for key, value in update_data.items():
        setattr(adsearch, key, value)

    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.delete("/{adsearch_id}", status_code=204)
def delete_adsearch(adsearch_id: int, session: DbSession):
    """Delete ad search together with its ads, scrape runs, and error logs."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    # Delete related scrape runs
    for run in session.exec(select(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id)).all():
        session.delete(run)

    # Delete related ads
    for ad in session.exec(select(Ad).where(Ad.adsearch_id == adsearch_id)).all():
        session.delete(ad)

    # Delete related error logs
    for log in session.exec(select(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id)).all():
        session.delete(log)

    session.delete(adsearch)
    session.commit()


@router.post("/{adsearch_id}/scrape", status_code=202)
def trigger_scrape(adsearch_id: int, session: DbSession):
    """Trigger an immediate scrape for the given AdSearch (async in background)."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    def _run_scrape() -> None:
        """Run scrape in a background thread; log errors to ErrorLog on failure."""
        with Session(db_engine) as bg_session:
            try:
                scraper = ScraperService(bg_session)
                fresh = bg_session.get(AdSearch, adsearch_id)
                if fresh:
                    scraper.scrape_adsearch(fresh)
            except Exception as e:
                logger.error(f"Triggered scrape failed for AdSearch {adsearch_id}: {e}")
                bg_session.add(
                    ErrorLog(
                        adsearch_id=adsearch_id,
                        error_type="ScrapeError",
                        message=str(e),
                        details=traceback.format_exc(),
                    )
                )
                bg_session.commit()

    threading.Thread(target=_run_scrape, daemon=True).start()

    return {"status": "scrape_triggered"}


# ---------------
# --- Helpers ---
# ---------------
def _validate_search_url_reachable(url: str) -> str | None:
    """Fetch URL, validate reachability; raise 422 on failure; return page title or None."""
    status, html = fetch_page_checked(url)
    if status == 0:
        raise HTTPException(
            status_code=422,
            detail=("URL konnte nicht aufgerufen werden. Bitte Internetverbindung und URL prüfen."),
        )
    if status == 404:
        raise HTTPException(
            status_code=422,
            detail=(
                "Die angegebene URL wurde nicht gefunden (404). Bitte eine "
                "gültige Kleinanzeigen-Suchergebnisseite eingeben."
            ),
        )
    if status >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Die Seite konnte nicht abgerufen werden (HTTP {status}). Bitte URL prüfen.",
        )
    return parse_search_title(html)
