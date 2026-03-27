"""API-Routen für Suchaufträge (Ad Searches)."""

import logging
import threading
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import DbSession, db_engine
from app.models.ad import Ad
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.scraper.httpclient import fetch_page_with_status
from app.scraper.parser import parse_search_title
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: DbSession):
    """Gibt alle Suchaufträge zurück."""
    return session.exec(select(AdSearch)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(adsearch_id: int, session: DbSession):
    """Gibt einen Suchauftrag anhand der ID zurück; 404 wenn nicht gefunden."""
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
    """Legt einen neuen Suchauftrag an; URL wird per Abruf validiert, Name aus Seitentitel wenn leer."""
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
    """Aktualisiert einen bestehenden Suchauftrag. 404 wenn nicht gefunden. URL wird bei Angabe validiert."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)

    # Bei geänderter URL Erreichbarkeit prüfen (und ggf. Seitentitel für leeren Namen nutzen).
    if "url" in update_data:
        _validate_search_url_reachable(update_data["url"])

    # Wenn der Client den Namen geleert hat: aktuelle URL laden und deren Titel als neuen Namen nutzen.
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
    """Löscht den Suchauftrag inklusive zugehöriger Anzeigen, Scrape-Läufe und Fehlerlogs."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    # Zugehörige Scrape-Läufe löschen
    for run in session.exec(select(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id)).all():
        session.delete(run)

    # Zugehörige KI-Analyse-Logs löschen
    for log in session.exec(
        select(AIAnalysisLog).where(AIAnalysisLog.adsearch_id == adsearch_id)
    ).all():
        session.delete(log)

    # Zugehörige Anzeigen löschen
    for ad in session.exec(select(Ad).where(Ad.adsearch_id == adsearch_id)).all():
        session.delete(ad)

    # Zugehörige Fehlerlogs löschen
    for log in session.exec(select(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id)).all():
        session.delete(log)

    session.delete(adsearch)
    session.commit()


@router.post("/{adsearch_id}/scrape", status_code=202)
def trigger_scrape(adsearch_id: int, session: DbSession):
    """Löst einen sofortigen Scrape für den Suchauftrag aus (asynchron im Hintergrund)."""
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    def _run_scrape() -> None:
        """Führt den Scrape in einem Hintergrund-Thread aus; bei Fehler in ErrorLog schreiben."""
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
# --- Hilfsfunktionen ---
# ---------------
def _validate_search_url_reachable(url: str) -> str | None:
    """Lädt die URL, prüft Erreichbarkeit; bei Fehler 422; gibt Seitentitel oder None zurück."""
    status, html = fetch_page_with_status(url)
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

