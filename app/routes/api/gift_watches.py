"""API-Routen für die Fundgrube (Verschenken-Beobachtung mit eigenem Regelwerk).

Eine ``GiftWatch`` ist der fachliche Datensatz (Interessensprofil, Schwerpunkte, Transport-
Profil); technisch erzeugt sie ein ``AdSearch``-Kind (Verschenken-Kategorie-URL + Umkreis),
das die erprobte Scrape-/Analyse-Pipeline unverändert weiterverarbeitet — dasselbe Muster
wie ``SearchOrder`` → ``AdSearch``.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func
from sqlmodel import Session, col, select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import SessionDep
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.gift_watch import (
    GiftWatch,
    GiftWatchCreate,
    GiftWatchRead,
    GiftWatchUpdate,
)
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.platforms import SearchParams, get_platform

router = APIRouter(prefix="/gift-watches", tags=["GiftWatches"])


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[GiftWatchRead])
def list_gift_watches(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt alle Fundgrube-Beobachtungen des Nutzers zurück (neueste zuerst)."""
    watches = session.exec(
        select(GiftWatch)
        .where(GiftWatch.owner_id == current_user.user_id)
        .order_by(col(GiftWatch.id).desc())
    ).all()
    result = [_build_read(session, watch) for watch in watches]
    session.rollback()
    return result


@router.get("/{watch_id}", response_model=GiftWatchRead)
def get_gift_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt eine Fundgrube-Beobachtung anhand der ID zurück; 404 wenn nicht gefunden."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    result = _build_read(session, watch)
    session.rollback()
    return result


@router.post("/", response_model=GiftWatchRead, status_code=201)
def create_gift_watch(
    data: GiftWatchCreate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt eine Fundgrube-Beobachtung an (inkl. AdSearch-Kind) und stößt eine erste Prüfung an."""
    name = data.name.strip() or f"Fundgrube {data.postal_code}"
    watch = GiftWatch(
        owner_id=current_user.user_id,
        name=name,
        postal_code=data.postal_code,
        radius_km=data.radius_km,
        interest_profile=data.interest_profile,
        focus_keywords=data.focus_keywords,
        exclude_keywords=data.exclude_keywords,
        exclude_categories=data.exclude_categories,
        vehicle=data.vehicle,
        can_carry_heavy=data.can_carry_heavy,
        min_score_notify=data.min_score_notify,
        is_active=data.is_active,
        scrape_interval_minutes=data.scrape_interval_minutes,
    )
    session.add(watch)
    session.flush()
    _sync_adsearch(session, watch)
    session.commit()
    session.refresh(watch)

    background_jobs.trigger_scrape_once()
    return _build_read(session, watch)


@router.patch("/{watch_id}", response_model=GiftWatchRead)
def update_gift_watch(
    watch_id: int,
    data: GiftWatchUpdate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Aktualisiert die Beobachtung und synchronisiert das AdSearch-Kind (URL/Filter)."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    update = data.model_dump(exclude_unset=True)
    if "name" in update and update["name"] is not None and update["name"].strip():
        update["name"] = update["name"].strip()
    elif "name" in update:
        del update["name"]  # leeren Namen nicht übernehmen
    for key, value in update.items():
        setattr(watch, key, value)
    session.add(watch)
    session.flush()
    _sync_adsearch(session, watch)
    session.commit()
    session.refresh(watch)
    return _build_read(session, watch)


@router.post("/{watch_id}/check-now", response_model=GiftWatchRead)
def check_gift_watch_now(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Macht das AdSearch-Kind sofort fällig und stößt den Hintergrund-Scrape an."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    child = _get_ad_child(session, watch.id)
    if child is not None:
        child.last_scraped_at = None
        session.add(child)
        session.commit()
        background_jobs.trigger_scrape_once()
    return _build_read(session, watch)


@router.delete("/{watch_id}", status_code=204)
def delete_gift_watch(
    watch_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Löscht die Beobachtung inklusive AdSearch-Kind, Funden und Logs."""
    watch = _get_owned_watch(session, watch_id, current_user.user_id)
    child = _get_ad_child(session, watch.id)
    if child is not None and child.id is not None:
        _delete_adsearch_cascade(session, child.id)
    session.delete(watch)
    session.commit()


# -----------------------
# --- Hilfsfunktionen ---
# -----------------------
def _get_owned_watch(session: Session, watch_id: int, owner_id: str) -> GiftWatch:
    """Lädt eine Fundgrube-Beobachtung des Nutzers oder wirft 404."""
    watch = session.exec(
        select(GiftWatch).where(GiftWatch.id == watch_id, GiftWatch.owner_id == owner_id)
    ).first()
    if not watch:
        raise HTTPException(status_code=404, detail="GiftWatch not found")
    return watch


def _get_ad_child(session: Session, watch_id: int | None) -> AdSearch | None:
    """Das AdSearch-Kind (Verschenken-Suche) einer Beobachtung, falls vorhanden."""
    if watch_id is None:
        return None
    return session.exec(select(AdSearch).where(AdSearch.gift_watch_id == watch_id)).first()


def _build_gift_url(watch: GiftWatch) -> str:
    """Leitet die Verschenken-Kategorie-URL im Umkreis der Nutzer-PLZ ab."""
    scraper = get_platform("kleinanzeigen").scraper
    return scraper.build_search_url(
        SearchParams(
            query="", postal_code=watch.postal_code, radius_km=watch.radius_km, gift_only=True
        )
    )


def _sync_adsearch(session: Session, watch: GiftWatch) -> None:
    """Legt das AdSearch-Kind an oder überträgt die aktuelle Regel-Konfiguration darauf."""
    assert watch.id is not None
    child = _get_ad_child(session, watch.id)
    url = _build_gift_url(watch)
    if child is None:
        child = AdSearch(
            owner_id=watch.owner_id,
            gift_watch_id=watch.id,
            name=watch.name,
            platform="kleinanzeigen",
            url=url,
            search_query=None,
        )
    child.name = watch.name
    child.url = url
    child.postal_code = watch.postal_code
    child.radius_km = watch.radius_km
    # Regeln, die deterministisch (gratis) im Scraper greifen, auf das Kind spiegeln.
    child.blacklist_keywords = watch.exclude_keywords
    child.blacklist_categories = watch.exclude_categories
    child.is_active = watch.is_active
    child.scrape_interval_minutes = watch.scrape_interval_minutes
    session.add(child)


def _delete_adsearch_cascade(session: Session, adsearch_id: int) -> None:
    """Löscht ein AdSearch-Kind inklusive Anzeigen, Scrape-Läufen und Logs."""
    session.execute(delete(AIAnalysisLog).where(AIAnalysisLog.adsearch_id == adsearch_id))
    session.execute(delete(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id))
    session.execute(delete(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id))
    session.execute(delete(Ad).where(Ad.adsearch_id == adsearch_id))
    session.execute(delete(AdSearch).where(AdSearch.id == adsearch_id))


def _build_read(session: Session, watch: GiftWatch) -> GiftWatchRead:
    """Baut die API-Ausgabe inkl. Fund-Zähler und letzter Prüfzeit aus dem AdSearch-Kind."""
    child = _get_ad_child(session, watch.id)
    read = GiftWatchRead.model_validate(watch)
    if child is not None:
        read.adsearch_id = child.id
        read.last_scraped_at = child.last_scraped_at
        read.ad_count = session.exec(
            select(func.count(col(Ad.id))).where(Ad.adsearch_id == child.id)
        ).one()
    return read
