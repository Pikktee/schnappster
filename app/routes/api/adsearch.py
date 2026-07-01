"""API-Routen für Suchaufträge (Ad Searches)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import SessionDep
from app.models.ad import Ad
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.platforms import (
    DEFAULT_PLATFORM,
    SearchParams,
    get_all_platform_names,
    get_platform,
)
from app.scraper.httpclient import fetch_page_with_status
from app.scraper.parser import parse_search_title

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: SessionDep, current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """Gibt alle Suchaufträge zurück."""
    searches = session.exec(select(AdSearch).where(AdSearch.owner_id == current_user.user_id)).all()
    result = [AdSearchRead.model_validate(search) for search in searches]
    session.rollback()
    return result


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(
    adsearch_id: int,
    session: SessionDep,
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

    result = AdSearchRead.model_validate(adsearch)
    session.rollback()
    return result


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(
    data: AdSearchCreate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt einen neuen Suchauftrag an.

    URL wird per Abruf validiert, Name bei leerem Input aus dem Seitentitel uebernommen.
    """
    name = data.name.strip()
    session.rollback()
    if data.platform not in get_all_platform_names():
        raise HTTPException(status_code=422, detail=f"Unbekannte Plattform '{data.platform}'.")
    effective_url = _resolve_search_url(data)

    if data.platform == DEFAULT_PLATFORM:
        # Kleinanzeigen: URL per Abruf validieren, leerer Name → Seitentitel.
        title_from_page = _validate_search_url_reachable(effective_url)
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
    elif not name:
        # eBay & Co.: URL ist selbst gebaut (deterministisch); ein direkter Abruf würde eBay
        # ohnehin blocken (der Scrape nutzt später den Proxy). Name aus dem Suchbegriff.
        name = _default_search_name(data.search_query)

    adsearch = AdSearch.model_validate(
        {
            **data.model_dump(),
            "name": name,
            "owner_id": current_user.user_id,
            "url": effective_url,
        }
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
    session: SessionDep,
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
    platform = adsearch.platform or DEFAULT_PLATFORM
    is_default_platform = platform == DEFAULT_PLATFORM

    # Keyword-Felder geändert und keine explizite URL: effektive Such-URL neu ableiten.
    keyword_fields = {"search_query", "postal_code", "radius_km", "min_price", "max_price"}
    if "url" not in update_data and keyword_fields & update_data.keys():
        merged_query = update_data.get("search_query", adsearch.search_query)
        if merged_query:
            scraper = get_platform(platform).scraper
            update_data["url"] = scraper.build_search_url(
                SearchParams(
                    query=merged_query,
                    postal_code=update_data.get("postal_code", adsearch.postal_code),
                    radius_km=update_data.get("radius_km", adsearch.radius_km),
                    min_price=update_data.get("min_price", adsearch.min_price),
                    max_price=update_data.get("max_price", adsearch.max_price),
                )
            )

    # Erreichbarkeit nur für Kleinanzeigen prüfen — eBay blockt direkte Abrufe; die URL ist
    # selbst gebaut (deterministisch), also nichts zu validieren.
    if "url" in update_data and is_default_platform:
        session.rollback()
        _validate_search_url_reachable(update_data["url"])

    # Leerer Name: bei Kleinanzeigen aus dem Seitentitel, sonst aus dem Suchbegriff.
    if (
        "name" in update_data
        and isinstance(update_data["name"], str)
        and not update_data["name"].strip()
    ):
        if is_default_platform:
            session.rollback()
            title_from_page = _validate_search_url_reachable(current_url)
            if not title_from_page:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Kein Seitentitel auf der Seite gefunden. Bitte URL prüfen "
                        "oder einen Namen manuell eingeben."
                    ),
                )
            update_data["name"] = title_from_page
        else:
            merged_query = update_data.get("search_query", adsearch.search_query)
            update_data["name"] = _default_search_name(merged_query)

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
    session: SessionDep,
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
def _resolve_search_url(data: AdSearchCreate) -> str:
    """Direkte URL oder – bei Keyword-Suche – aus Suchbegriff/PLZ/Radius/Preis abgeleitete URL."""
    if data.url:
        return data.url
    scraper = get_platform(data.platform).scraper
    return scraper.build_search_url(
        SearchParams(
            query=data.search_query or "",
            postal_code=data.postal_code,
            radius_km=data.radius_km,
            min_price=data.min_price,
            max_price=data.max_price,
        )
    )


def _default_search_name(query: str | None) -> str:
    """Fallback-Name für Quellen ohne Seitentitel-Abruf (z. B. eBay): aus dem Suchbegriff."""
    cleaned = (query or "").strip()
    return cleaned if cleaned else "Suche"


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
