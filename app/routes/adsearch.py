import logging
import threading
import traceback

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

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
    """
    Returns all ad searches (Suchaufträge).
    """
    return session.exec(select(AdSearch)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(adsearch_id: int, session: DbSession):
    """
    Returns a specific ad search (Suchauftrag).

    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    return adsearch


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(data: AdSearchCreate, session: DbSession):
    """
    Create a new ad search (Suchauftrag).

    The URL is always validated by fetching the page (reachability, no 404).
    If `name` is empty, the page title is fetched from the search URL and used
    as the name. A 422 is returned if the page cannot be reached or yields no
    recognisable title when name is empty.
    """
    name = data.name.strip()
    title_from_page = _validate_search_url_reachable(data.url)

    if not name:
        if not title_from_page:
            raise HTTPException(
                status_code=422,
                detail="Kein Seitentitel auf der Seite gefunden. Bitte URL prüfen oder einen Namen manuell eingeben.",
            )
        name = title_from_page

    adsearch = AdSearch.model_validate({**data.model_dump(), "name": name})

    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.patch("/{adsearch_id}", response_model=AdSearchRead)
def update_adsearch(adsearch_id: int, data: AdSearchUpdate, session: DbSession):
    """
    Update an existing ad search (Suchauftrag).

    If the URL is being updated, it is validated by fetching the page (reachability, no 404).
    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)

    if "url" in update_data:
        _validate_search_url_reachable(update_data["url"])

    for key, value in update_data.items():
        setattr(adsearch, key, value)

    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.delete("/{adsearch_id}", status_code=204)
def delete_adsearch(adsearch_id: int, session: DbSession):
    """
    Delete an ad search (Suchauftrag)

    If the given ID does not exist, an error 404 is thrown.

    Related ads and error logs are preserved (their adsearch_id is set to NULL).
    Related scrape runs are deleted.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    # Delete related scrape runs (they require an adsearch_id)
    for run in session.exec(select(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id)).all():
        session.delete(run)

    # Set adsearch_id to NULL for related ads (they can exist independently)
    for ad in session.exec(select(Ad).where(Ad.adsearch_id == adsearch_id)).all():
        ad.adsearch_id = None

    # Set adsearch_id to NULL for related error logs (they can exist independently)
    for log in session.exec(select(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id)).all():
        log.adsearch_id = None

    session.delete(adsearch)
    session.commit()


@router.post("/{adsearch_id}/scrape", status_code=202)
def trigger_scrape(adsearch_id: int, session: DbSession):
    """
    Trigger an immediate scrape for a specific AdSearch.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    def _run_scrape() -> None:
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
    """
    Fetch the search URL and validate it is reachable and returns a valid page.
    Raises HTTPException 422 on failure. Returns the parsed page title, or None if not parseable.
    """
    status, html = fetch_page_checked(url)
    if status == 0:
        raise HTTPException(
            status_code=422,
            detail="URL konnte nicht aufgerufen werden. Bitte Internetverbindung und URL prüfen.",
        )
    if status == 404:
        raise HTTPException(
            status_code=422,
            detail="Die angegebene URL wurde nicht gefunden (404). Bitte eine gültige Kleinanzeigen-Suchergebnisseite eingeben.",
        )
    if status >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Die Seite konnte nicht abgerufen werden (HTTP {status}). Bitte URL prüfen.",
        )
    return parse_search_title(html)
