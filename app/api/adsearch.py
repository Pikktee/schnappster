import logging
import threading

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.core.db import DbSession, engine
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


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
    Create a new ad search (Suchauftrag)
    """
    adsearch = AdSearch.model_validate(data)

    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.patch("/{adsearch_id}", response_model=AdSearchRead)
def update_adsearch(adsearch_id: int, data: AdSearchUpdate, session: DbSession):
    """
    Update an existing ad search (Suchauftrag)

    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)

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
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    session.delete(adsearch)
    session.commit()


@router.post("/{adsearch_id}/scrape", status_code=202)
def trigger_scrape(adsearch_id: int, session: DbSession):
    """Trigger an immediate scrape for a specific AdSearch."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    def _run_scrape() -> None:
        with Session(engine) as bg_session:
            try:
                scraper = ScraperService(bg_session)
                fresh = bg_session.get(AdSearch, adsearch_id)
                if fresh:
                    scraper.scrape_adsearch(fresh)
            except Exception as e:
                logger.error(f"Triggered scrape failed for AdSearch {adsearch_id}: {e}")

    threading.Thread(target=_run_scrape, daemon=True).start()

    return {"status": "scrape_triggered"}
