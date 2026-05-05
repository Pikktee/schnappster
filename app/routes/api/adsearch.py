"""API-Routen für Suchaufträge (Ad Searches)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import UserDbSession, set_user_db_claims
from app.models.ad import Ad
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.scraper.httpclient import fetch_page_with_status
from app.scraper.parser import parse_search_title

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: UserDbSession, current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """Gibt alle Suchaufträge zurück."""
    return session.exec(select(AdSearch).where(AdSearch.owner_id == current_user.user_id)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(
    adsearch_id: int,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt einen Suchauftrag anhand der ID zurück; 404 wenn nicht gefunden."""
    adsearch = session.exec(
        select(AdSearch).where(
            AdSearch.id == adsearch_id,
            AdSearch.owner_id == current_user.user_id,
        )
    ).first()

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    return adsearch


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(
    data: AdSearchCreate,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt einen neuen Suchauftrag an.

    URL wird per Abruf validiert, Name bei leerem Input aus dem Seitentitel uebernommen.
    """
    name = data.name.strip()
    session.rollback()
    title_from_page = _validate_search_url_reachable(data.url)
    set_user_db_claims(session, current_user)

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

    adsearch = AdSearch.model_validate(
        {**data.model_dump(), "name": name, "owner_id": current_user.user_id}
    )

    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)
    background_jobs.trigger_scrape_once()

    return adsearch


@router.patch("/{adsearch_id}", response_model=AdSearchRead)
def update_adsearch(
    adsearch_id: int,
    data: AdSearchUpdate,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Aktualisiert einen bestehenden Suchauftrag.

    404 bei unbekannter ID; URL wird bei Angabe serverseitig validiert.
    """
    adsearch = session.exec(
        select(AdSearch).where(
            AdSearch.id == adsearch_id,
            AdSearch.owner_id == current_user.user_id,
        )
    ).first()

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)
    current_url = adsearch.url

    # Bei geänderter URL Erreichbarkeit prüfen (und ggf. Seitentitel für leeren Namen nutzen).
    if "url" in update_data:
        session.rollback()
        _validate_search_url_reachable(update_data["url"])

    # Wenn der Client den Namen leert, nutzen wir den Seitentitel der aktuellen URL.
    title_from_page: str | None = None
    if (
        "name" in update_data
        and isinstance(update_data["name"], str)
        and not update_data["name"].strip()
    ):
        session.rollback()
        title_from_page = _validate_search_url_reachable(current_url)

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

    set_user_db_claims(session, current_user)
    adsearch = session.exec(
        select(AdSearch).where(
            AdSearch.id == adsearch_id,
            AdSearch.owner_id == current_user.user_id,
        )
    ).first()
    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    for key, value in update_data.items():
        setattr(adsearch, key, value)

    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.delete("/{adsearch_id}", status_code=204)
def delete_adsearch(
    adsearch_id: int,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Löscht den Suchauftrag inklusive zugehöriger Anzeigen, Scrape-Läufe und Fehlerlogs."""
    adsearch = session.exec(
        select(AdSearch).where(
            AdSearch.id == adsearch_id,
            AdSearch.owner_id == current_user.user_id,
        )
    ).first()

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    session.execute(delete(AIAnalysisLog).where(AIAnalysisLog.adsearch_id == adsearch_id))
    session.execute(delete(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id))
    session.execute(delete(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id))
    session.execute(delete(Ad).where(Ad.adsearch_id == adsearch_id))
    session.execute(
        delete(AdSearch).where(
            AdSearch.id == adsearch_id,
            AdSearch.owner_id == current_user.user_id,
        )
    )
    session.commit()


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
