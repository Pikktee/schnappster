"""API-Routen für Deal-Alarme (MyDealz-Schlagwort-Watcher)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import col, select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import SessionDep
from app.models.deal_watch import (
    Deal,
    DealPreview,
    DealRead,
    DealWatch,
    DealWatchCreate,
    DealWatchPreviewRequest,
    DealWatchPreviewResponse,
    DealWatchRead,
    DealWatchUpdate,
)
from app.scraper import mydealz
from app.services.deal_watch import DealWatchService

router = APIRouter(prefix="/deal-watches", tags=["DealWatches"])


# --------------
# --- Routen ---
# --------------
@router.post("/preview", response_model=DealWatchPreviewResponse)
def preview_deal_watch(
    data: DealWatchPreviewRequest,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Holt aktuelle MyDealz-Deals zum Suchbegriff (speichert nichts) — Vorschau vor dem Anlegen."""
    session.rollback()  # Verbindung vor dem externen Abruf freigeben
    status, html = mydealz.fetch_deals_html(mydealz.build_search_url(data.query))
    if not mydealz.is_usable(status, html):
        raise HTTPException(
            status_code=422,
            detail="MyDealz ist gerade nicht erreichbar. Bitte später erneut versuchen.",
        )
    deals = mydealz.parse_deals(html)
    previews = [
        DealPreview(
            external_id=d.external_id,
            title=d.title,
            url=d.url,
            temperature=d.temperature,
            price=d.price,
            next_best_price=d.next_best_price,
            merchant=d.merchant,
        )
        for d in deals
    ]
    return DealWatchPreviewResponse(deals=previews)


@router.get("/", response_model=list[DealWatchRead])
def list_deal_watches(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt alle Deal-Alarme des Nutzers zurück (neueste zuerst)."""
    watches = session.exec(
        select(DealWatch)
        .where(DealWatch.owner_id == current_user.user_id)
        .order_by(col(DealWatch.id).desc())
    ).all()
    result = [DealWatchRead.model_validate(watch) for watch in watches]
    session.rollback()
    return result


@router.get("/{watch_id}", response_model=DealWatchRead)
def get_deal_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt einen Deal-Alarm anhand der ID zurück; 404 wenn nicht gefunden."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    result = DealWatchRead.model_validate(watch)
    session.rollback()
    return result


@router.get("/{watch_id}/deals", response_model=list[DealRead])
def get_deal_watch_deals(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt die gefundenen Deals eines Alarms zurück (heißeste zuerst)."""
    _get_owned_watch(session, watch_id, current_user.user_id)
    deals = session.exec(
        select(Deal)
        .where(Deal.deal_watch_id == watch_id)
        .order_by(col(Deal.temperature).desc().nullslast())
    ).all()
    result = [DealRead.model_validate(deal) for deal in deals]
    session.rollback()
    return result


@router.post("/", response_model=DealWatchRead, status_code=201)
def create_deal_watch(
    data: DealWatchCreate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt einen Deal-Alarm an und stößt eine erste (stille Baseline-)Prüfung an."""
    name = data.name.strip() or data.query.strip()
    watch = DealWatch.model_validate(
        {**data.model_dump(), "name": name, "owner_id": current_user.user_id}
    )
    session.add(watch)
    session.commit()
    session.refresh(watch)
    background_jobs.trigger_deal_check_once()
    return watch


@router.patch("/{watch_id}", response_model=DealWatchRead)
def update_deal_watch(
    watch_id: int,
    data: DealWatchUpdate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Aktualisiert Name, Schwelle, Intervall oder Aktiv-Status; 404 bei unbekannter ID."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(watch, key, value)
    session.commit()
    session.refresh(watch)
    return watch


@router.post("/{watch_id}/check-now", response_model=DealWatchRead)
def check_deal_watch_now(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Prüft den Deal-Alarm sofort (synchron) und gibt den aktualisierten Alarm zurück."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    DealWatchService(session).check_watch(watch)
    updated = session.get(DealWatch, watch_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="DealWatch not found")
    return DealWatchRead.model_validate(updated)


@router.delete("/{watch_id}", status_code=204)
def delete_deal_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Löscht den Deal-Alarm inklusive gefundener Deals."""
    _get_owned_watch(session, watch_id, current_user.user_id)
    session.execute(delete(Deal).where(Deal.deal_watch_id == watch_id))
    session.execute(
        delete(DealWatch).where(
            DealWatch.id == watch_id,
            DealWatch.owner_id == current_user.user_id,
        )
    )
    session.commit()


# -----------------------
# --- Hilfsfunktionen ---
# -----------------------
def _get_owned_watch(session: SessionDep, watch_id: int, owner_id: str) -> DealWatch:
    """Lädt einen Deal-Alarm des Nutzers oder wirft 404."""
    watch = session.exec(
        select(DealWatch).where(
            DealWatch.id == watch_id,
            DealWatch.owner_id == owner_id,
        )
    ).first()
    if not watch:
        raise HTTPException(status_code=404, detail="DealWatch not found")
    return watch
