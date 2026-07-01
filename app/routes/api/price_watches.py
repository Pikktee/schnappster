"""API-Routen für Preis-Alarme (generisches Webseiten-Preis-Monitoring)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import SessionDep
from app.models.price_watch import (
    PricePoint,
    PricePointRead,
    PriceWatch,
    PriceWatchCreate,
    PriceWatchPreviewRequest,
    PriceWatchPreviewResponse,
    PriceWatchRead,
    PriceWatchUpdate,
)
from app.scraper.httpclient import fetch_page_with_status
from app.services.price_extractor import extract_candidates, parse_title, refine_with_ai
from app.services.price_watch import PriceWatchService

router = APIRouter(prefix="/price-watches", tags=["PriceWatches"])


# --------------
# --- Routen ---
# --------------
@router.post("/preview", response_model=PriceWatchPreviewResponse)
def preview_price_watch(
    data: PriceWatchPreviewRequest,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Lädt die URL und schlägt mögliche Preisangaben zur Auswahl vor (speichert nichts)."""
    session.rollback()  # Verbindung vor dem externen Abruf freigeben
    html = _fetch_or_422(data.url)
    title = parse_title(html)
    candidates = refine_with_ai(extract_candidates(html), title)
    return PriceWatchPreviewResponse(title=title, candidates=candidates)


@router.get("/", response_model=list[PriceWatchRead])
def list_price_watches(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt alle Preis-Alarme des Nutzers zurück."""
    watches = session.exec(
        select(PriceWatch).where(PriceWatch.owner_id == current_user.user_id)
    ).all()
    result = [PriceWatchRead.model_validate(watch) for watch in watches]
    session.rollback()
    return result


@router.get("/{watch_id}", response_model=PriceWatchRead)
def get_price_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt einen Preis-Alarm anhand der ID zurück; 404 wenn nicht gefunden."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    result = PriceWatchRead.model_validate(watch)
    session.rollback()
    return result


@router.get("/{watch_id}/history", response_model=list[PricePointRead])
def get_price_history(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt den Preisverlauf (älteste zuerst) für den Verlaufsgraphen zurück."""
    _get_owned_watch(session, watch_id, current_user.user_id)
    points = session.exec(
        select(PricePoint)
        .where(PricePoint.pricewatch_id == watch_id)
        .order_by(PricePoint.recorded_at)
    ).all()
    result = [PricePointRead.model_validate(point) for point in points]
    session.rollback()
    return result


@router.post("/", response_model=PriceWatchRead, status_code=201)
def create_price_watch(
    data: PriceWatchCreate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt einen Preis-Alarm an (nach Auswahl der Preisangabe) und stößt eine erste Prüfung an."""
    name = data.name.strip()
    if not name:
        session.rollback()
        status, html = fetch_page_with_status(data.url, via_proxy=True)
        name = (parse_title(html) if status == 200 else None) or data.url

    watch = PriceWatch.model_validate(
        {**data.model_dump(), "name": name, "owner_id": current_user.user_id}
    )
    session.add(watch)
    session.commit()
    session.refresh(watch)
    background_jobs.trigger_price_check_once()
    return watch


@router.patch("/{watch_id}", response_model=PriceWatchRead)
def update_price_watch(
    watch_id: int,
    data: PriceWatchUpdate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Aktualisiert Name, Intervall, Schwelle oder Aktiv-Status; 404 bei unbekannter ID."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(watch, key, value)
    session.commit()
    session.refresh(watch)
    return watch


@router.post("/{watch_id}/check-now", response_model=PriceWatchRead)
def check_price_watch_now(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Prüft den Preis sofort (synchron) und gibt den aktualisierten Alarm zurück."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    PriceWatchService(session).check_watch(watch)
    updated = session.get(PriceWatch, watch_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="PriceWatch not found")
    return PriceWatchRead.model_validate(updated)


@router.delete("/{watch_id}", status_code=204)
def delete_price_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Löscht den Preis-Alarm inklusive zugehöriger Preis-Datenpunkte."""
    _get_owned_watch(session, watch_id, current_user.user_id)
    session.execute(delete(PricePoint).where(PricePoint.pricewatch_id == watch_id))
    session.execute(
        delete(PriceWatch).where(
            PriceWatch.id == watch_id,
            PriceWatch.owner_id == current_user.user_id,
        )
    )
    session.commit()


# -----------------------
# --- Hilfsfunktionen ---
# -----------------------
def _get_owned_watch(session: SessionDep, watch_id: int, owner_id: str) -> PriceWatch:
    """Lädt einen Watch des Nutzers oder wirft 404."""
    watch = session.exec(
        select(PriceWatch).where(
            PriceWatch.id == watch_id,
            PriceWatch.owner_id == owner_id,
        )
    ).first()
    if not watch:
        raise HTTPException(status_code=404, detail="PriceWatch not found")
    return watch


_BOT_BLOCK_STATUS = {403, 429, 503}
_BOT_CHALLENGE_MARKERS = ("just a moment", "enable javascript and cookies", "cf-challenge")
_BOT_BLOCK_DETAIL = (
    "Die Seite ist durch einen Bot-Schutz (z. B. Cloudflare) geschützt und lässt sich "
    "nicht automatisch auslesen. Ein Preis-Alarm ist für diese Seite leider nicht möglich."
)


def _fetch_or_422(url: str) -> str:
    """Lädt die URL; wirft 422 bei Nicht-Erreichbarkeit/Bot-Schutz; gibt HTML zurück."""
    status, html = fetch_page_with_status(url, via_proxy=True)
    if status == 0:
        raise HTTPException(
            status_code=422,
            detail="Die Webseite konnte nicht aufgerufen werden. Bitte URL und Verbindung prüfen.",
        )
    if status in _BOT_BLOCK_STATUS or _looks_like_bot_challenge(html):
        raise HTTPException(status_code=422, detail=_BOT_BLOCK_DETAIL)
    if status >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Die Seite konnte nicht abgerufen werden (HTTP {status}). Bitte URL prüfen.",
        )
    return html


def _looks_like_bot_challenge(html: str) -> bool:
    """Erkennt eine JS-/Cookie-Challenge-Seite (Cloudflare & Co.), die als HTTP 200 kommt."""
    if not html or len(html) > 20000:
        return False
    low = html.lower()
    return any(marker in low for marker in _BOT_CHALLENGE_MARKERS)
