"""API-Routen für vereinheitlichte Suchaufträge (SearchOrder = Eltern der Quellen-Kinder).

Ein Suchauftrag bündelt EINEN Suchbegriff über die Quellen Kleinanzeigen/eBay (``AdSearch``)
und MyDealz (``DealWatch``). Die Routen verwalten Eltern + Kinder als eine Einheit; die
Scrape-/Check-Pipelines bleiben unangetastet und arbeiten weiter auf den Kindern.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func
from sqlmodel import Session, col, select

from app.core.auth import CurrentUser, get_current_user
from app.core.background_jobs import BackgroundJobs, get_background_jobs
from app.core.db import SessionDep
from app.models.ad import Ad
from app.models.adsearch import AdSearch, AdSearchRead
from app.models.deal_watch import MIN_DEAL_INTERVAL_MINUTES, Deal, DealWatch, DealWatchRead
from app.models.logs_aianalysis import AIAnalysisLog
from app.models.logs_error import ErrorLog
from app.models.logs_scraperun import ScrapeRun
from app.models.search_order import (
    SearchOrder,
    SearchOrderCreate,
    SearchOrderRead,
    SearchOrderUpdate,
)
from app.platforms import SearchParams, get_platform

router = APIRouter(prefix="/search-orders", tags=["SearchOrders"])

_AD_PLATFORMS = ("kleinanzeigen", "ebay")


# --------------
# --- Routen ---
# --------------
@router.get("/", response_model=list[SearchOrderRead])
def list_search_orders(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt alle Suchaufträge zurück (neueste zuerst); adoptiert vorher verwaiste Alt-Suchen."""
    _adopt_orphans(session, current_user.user_id)
    orders = session.exec(
        select(SearchOrder)
        .where(SearchOrder.owner_id == current_user.user_id)
        .order_by(col(SearchOrder.id).desc())
    ).all()
    result = [_build_read(session, order) for order in orders]
    session.rollback()
    return result


@router.get("/{order_id}", response_model=SearchOrderRead)
def get_search_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt einen Suchauftrag mit seinen Quellen-Kindern zurück; 404 wenn nicht gefunden."""
    order = _get_owned_order(session, order_id, current_user.user_id)
    result = _build_read(session, order)
    session.rollback()
    return result


@router.post("/", response_model=SearchOrderRead, status_code=201)
def create_search_order(
    data: SearchOrderCreate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Legt einen Suchauftrag an (Eltern + je gewählter Quelle ein Kind) und stößt Checks an."""
    name = data.name.strip() or data.query.strip()
    order = SearchOrder(owner_id=current_user.user_id, name=name, query=data.query)
    session.add(order)
    session.flush()

    _sync_children(session, order, data)
    session.commit()
    session.refresh(order)

    if data.use_kleinanzeigen or data.use_ebay:
        background_jobs.trigger_scrape_once()
    if data.use_mydealz:
        background_jobs.trigger_deal_check_once()
    return _build_read(session, order)


@router.patch("/{order_id}", response_model=SearchOrderRead)
def update_search_order(
    order_id: int,
    data: SearchOrderUpdate,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Aktualisiert Eltern + Kinder; neue Quellen werden angelegt, abgewählte entfernt."""
    order = _get_owned_order(session, order_id, current_user.user_id)
    update = data.model_dump(exclude_unset=True)

    if "name" in update and update["name"] is not None and update["name"].strip():
        order.name = update["name"].strip()
    if "query" in update and update["query"] is not None and update["query"].strip():
        order.query = update["query"].strip()
    if "is_active" in update and update["is_active"] is not None:
        order.is_active = update["is_active"]

    # Zielzustand aus bestehender Kind-Konfiguration + Update-Feldern mischen.
    merged = _merge_config(session, order, update)
    added_sources = _sync_children(session, order, merged)
    session.add(order)
    session.commit()
    session.refresh(order)

    if added_sources & {"kleinanzeigen", "ebay"}:
        background_jobs.trigger_scrape_once()
    if "mydealz" in added_sources:
        background_jobs.trigger_deal_check_once()
    return _build_read(session, order)


@router.post("/{order_id}/check-now", response_model=SearchOrderRead)
def check_search_order_now(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    background_jobs: BackgroundJobs = Depends(get_background_jobs),  # noqa: B008
):
    """Macht alle Kinder sofort fällig und stößt die Hintergrund-Checks an."""
    order = _get_owned_order(session, order_id, current_user.user_id)
    ad_children = _get_ad_children(session, order_id)
    watch = _get_deal_child(session, order_id)

    for child in ad_children.values():
        child.last_scraped_at = None
        session.add(child)
    if watch is not None:
        # Nicht auf None setzen: das würde den nächsten Check als stille Baseline werten
        # (keine Alarme). Stattdessen weit genug zurückdatieren, dass er fällig ist.
        watch.last_checked_at = datetime.now(UTC) - timedelta(
            minutes=watch.scrape_interval_minutes + 1
        )
        session.add(watch)
    session.commit()

    if ad_children:
        background_jobs.trigger_scrape_once()
    if watch is not None:
        background_jobs.trigger_deal_check_once()
    return _build_read(session, order)


@router.delete("/{order_id}", status_code=204)
def delete_search_order(
    order_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Löscht den Suchauftrag inklusive aller Quellen-Kinder und deren Funde."""
    order = _get_owned_order(session, order_id, current_user.user_id)
    for child in _get_ad_children(session, order_id).values():
        _delete_adsearch_cascade(session, child.id)  # type: ignore[arg-type]
    watch = _get_deal_child(session, order_id)
    if watch is not None:
        session.execute(delete(Deal).where(Deal.deal_watch_id == watch.id))
        session.delete(watch)
    session.delete(order)
    session.commit()


# -----------------------
# --- Hilfsfunktionen ---
# -----------------------
def _get_owned_order(session: Session, order_id: int, owner_id: str) -> SearchOrder:
    """Lädt einen Suchauftrag des Nutzers oder wirft 404."""
    order = session.exec(
        select(SearchOrder).where(
            SearchOrder.id == order_id, SearchOrder.owner_id == owner_id
        )
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="SearchOrder not found")
    return order


def _get_ad_children(session: Session, order_id: int) -> dict[str, AdSearch]:
    """Die AdSearch-Kinder des Auftrags, nach Plattform gemappt."""
    children = session.exec(
        select(AdSearch).where(AdSearch.search_order_id == order_id)
    ).all()
    return {child.platform or "kleinanzeigen": child for child in children}


def _get_deal_child(session: Session, order_id: int) -> DealWatch | None:
    """Das MyDealz-Kind des Auftrags (oder None)."""
    return session.exec(
        select(DealWatch).where(DealWatch.search_order_id == order_id)
    ).first()


def _build_search_url(platform: str, cfg: SearchOrderCreate, query: str) -> str:
    """Leitet die effektive Such-URL der Plattform deterministisch aus dem Suchbegriff ab."""
    scraper = get_platform(platform).scraper
    is_kleinanzeigen = platform == "kleinanzeigen"
    return scraper.build_search_url(
        SearchParams(
            query=query,
            postal_code=cfg.postal_code if is_kleinanzeigen else None,
            radius_km=cfg.radius_km if is_kleinanzeigen else None,
            min_price=cfg.min_price,
            max_price=cfg.max_price,
        )
    )


def _sync_children(session: Session, order: SearchOrder, cfg: SearchOrderCreate) -> set[str]:
    """Stellt den Ziel-Quellenzustand her (anlegen/aktualisieren/entfernen); neue Quellen zurück."""
    assert order.id is not None
    ad_children = _get_ad_children(session, order.id)
    wanted = {"kleinanzeigen": cfg.use_kleinanzeigen, "ebay": cfg.use_ebay}
    added: set[str] = set()

    for platform in _AD_PLATFORMS:
        child = ad_children.get(platform)
        if wanted[platform] and child is None:
            session.add(_new_ad_child(order, platform, cfg))
            added.add(platform)
        elif wanted[platform] and child is not None:
            _apply_ad_config(child, order, platform, cfg)
            session.add(child)
        elif not wanted[platform] and child is not None:
            _delete_adsearch_cascade(session, child.id)  # type: ignore[arg-type]

    watch = _get_deal_child(session, order.id)
    if cfg.use_mydealz and watch is None:
        session.add(_new_deal_child(order, cfg))
        added.add("mydealz")
    elif cfg.use_mydealz and watch is not None:
        _apply_deal_config(watch, order, cfg)
        session.add(watch)
    elif not cfg.use_mydealz and watch is not None:
        session.execute(delete(Deal).where(Deal.deal_watch_id == watch.id))
        session.delete(watch)
    return added


def _new_ad_child(order: SearchOrder, platform: str, cfg: SearchOrderCreate) -> AdSearch:
    """Baut ein neues AdSearch-Kind (Kleinanzeigen oder eBay) aus der Auftrags-Konfiguration."""
    child = AdSearch(
        owner_id=order.owner_id,
        search_order_id=order.id,
        name=order.name,
        platform=platform,
        url="",  # wird direkt darunter abgeleitet
        search_query=order.query,
        is_active=order.is_active,
    )
    _apply_ad_config(child, order, platform, cfg)
    return child


def _apply_ad_config(
    child: AdSearch, order: SearchOrder, platform: str, cfg: SearchOrderCreate
) -> None:
    """Überträgt die aktuelle Auftrags-Konfiguration auf ein AdSearch-Kind."""
    is_kleinanzeigen = platform == "kleinanzeigen"
    child.name = order.name
    child.is_active = order.is_active
    child.postal_code = cfg.postal_code if is_kleinanzeigen else None
    child.radius_km = cfg.radius_km if is_kleinanzeigen else None
    child.min_price = cfg.min_price
    child.max_price = cfg.max_price
    child.blacklist_keywords = cfg.blacklist_keywords
    child.prompt_addition = cfg.prompt_addition
    child.is_exclude_images = cfg.is_exclude_images
    child.scrape_interval_minutes = cfg.scrape_interval_minutes
    # URL nur bei Keyword-Suchen neu ableiten — adoptierte URL-Suchen behalten ihre URL.
    if order.query.strip():
        child.search_query = order.query
        child.url = _build_search_url(platform, cfg, order.query)


def _new_deal_child(order: SearchOrder, cfg: SearchOrderCreate) -> DealWatch:
    """Baut ein neues DealWatch-Kind (MyDealz) aus der Auftrags-Konfiguration."""
    watch = DealWatch(
        owner_id=order.owner_id,
        search_order_id=order.id,
        name=order.name,
        query=order.query,
        is_active=order.is_active,
    )
    _apply_deal_config(watch, order, cfg)
    return watch


def _apply_deal_config(watch: DealWatch, order: SearchOrder, cfg: SearchOrderCreate) -> None:
    """Überträgt die aktuelle Auftrags-Konfiguration auf das MyDealz-Kind."""
    watch.name = order.name
    watch.is_active = order.is_active
    if order.query.strip():
        watch.query = order.query
    watch.max_price = cfg.mydealz_max_price
    watch.min_temperature = cfg.mydealz_min_temperature
    watch.min_heating_velocity = cfg.mydealz_min_heating_velocity
    # MyDealz braucht kein Minuten-Polling; unter dem Deal-Minimum wird geclampt.
    watch.scrape_interval_minutes = max(cfg.scrape_interval_minutes, MIN_DEAL_INTERVAL_MINUTES)


def _merge_config(
    session: Session, order: SearchOrder, update: dict
) -> SearchOrderCreate:
    """Mischt die bestehende Kind-Konfiguration mit den Update-Feldern zum Vollbild."""
    assert order.id is not None
    ad_children = _get_ad_children(session, order.id)
    watch = _get_deal_child(session, order.id)
    any_ad = ad_children.get("kleinanzeigen") or ad_children.get("ebay")
    ka = ad_children.get("kleinanzeigen")

    current = {
        "query": order.query or "leer",  # nur für die Validierung; Eltern-query bleibt führend
        "use_kleinanzeigen": "kleinanzeigen" in ad_children,
        "use_ebay": "ebay" in ad_children,
        "use_mydealz": watch is not None,
        "postal_code": ka.postal_code if ka else None,
        "radius_km": ka.radius_km if ka else None,
        "min_price": any_ad.min_price if any_ad else None,
        "max_price": any_ad.max_price if any_ad else None,
        "blacklist_keywords": any_ad.blacklist_keywords if any_ad else None,
        "prompt_addition": any_ad.prompt_addition if any_ad else None,
        "is_exclude_images": any_ad.is_exclude_images if any_ad else False,
        "scrape_interval_minutes": (
            any_ad.scrape_interval_minutes
            if any_ad
            else (watch.scrape_interval_minutes if watch else 60)
        ),
        "mydealz_max_price": watch.max_price if watch else None,
        "mydealz_min_temperature": watch.min_temperature if watch else None,
        "mydealz_min_heating_velocity": watch.min_heating_velocity if watch else None,
    }
    allowed = set(current.keys()) - {"query"}
    current.update({k: v for k, v in update.items() if k in allowed})
    return SearchOrderCreate.model_validate(current)


def _delete_adsearch_cascade(session: Session, adsearch_id: int) -> None:
    """Löscht ein AdSearch-Kind inklusive Anzeigen, Scrape-Läufen und Logs."""
    session.execute(delete(AIAnalysisLog).where(AIAnalysisLog.adsearch_id == adsearch_id))
    session.execute(delete(ErrorLog).where(ErrorLog.adsearch_id == adsearch_id))
    session.execute(delete(ScrapeRun).where(ScrapeRun.adsearch_id == adsearch_id))
    session.execute(delete(Ad).where(Ad.adsearch_id == adsearch_id))
    session.execute(delete(AdSearch).where(AdSearch.id == adsearch_id))


def _adopt_orphans(session: Session, owner_id: str) -> None:
    """Erzeugt Eltern für verwaiste Alt-/Extension-Suchen (idempotent, verlustfrei).

    Die Chrome-Extension und Alt-Bestände legen AdSearch/DealWatch direkt an; damit sie im
    vereinheitlichten UI erscheinen, bekommt jedes verwaiste Kind hier seinen Eltern-Datensatz.
    """
    orphan_searches = session.exec(
        select(AdSearch).where(
            AdSearch.owner_id == owner_id, col(AdSearch.search_order_id).is_(None)
        )
    ).all()
    orphan_watches = session.exec(
        select(DealWatch).where(
            DealWatch.owner_id == owner_id, col(DealWatch.search_order_id).is_(None)
        )
    ).all()
    if not orphan_searches and not orphan_watches:
        return

    for child in orphan_searches:
        order = SearchOrder(
            owner_id=owner_id,
            name=child.name,
            query=child.search_query or "",
            is_active=child.is_active,
        )
        session.add(order)
        session.flush()
        child.search_order_id = order.id
        session.add(child)
    for watch in orphan_watches:
        order = SearchOrder(
            owner_id=owner_id, name=watch.name, query=watch.query, is_active=watch.is_active
        )
        session.add(order)
        session.flush()
        watch.search_order_id = order.id
        session.add(watch)
    session.commit()


def _build_read(session: Session, order: SearchOrder) -> SearchOrderRead:
    """Baut die API-Ausgabe mit Kindern, Fund-Zählern und letzter Prüfzeit."""
    assert order.id is not None
    ad_children = _get_ad_children(session, order.id)
    watch = _get_deal_child(session, order.id)

    child_ids = [child.id for child in ad_children.values() if child.id is not None]
    ad_count = 0
    if child_ids:
        ad_count = session.exec(
            select(func.count(col(Ad.id))).where(col(Ad.adsearch_id).in_(child_ids))
        ).one()
    deal_count = 0
    if watch is not None:
        deal_count = session.exec(
            select(func.count(col(Deal.id))).where(Deal.deal_watch_id == watch.id)
        ).one()

    checked = [child.last_scraped_at for child in ad_children.values()]
    checked.append(watch.last_checked_at if watch else None)
    known = [ts for ts in checked if ts is not None]

    # Kinder explizit in Read-Schemas wandeln — nach session.rollback() wären die ORM-Objekte
    # expired und würden still als null serialisiert.
    ka_child = ad_children.get("kleinanzeigen")
    ebay_child = ad_children.get("ebay")
    read = SearchOrderRead.model_validate(order)
    read.kleinanzeigen = AdSearchRead.model_validate(ka_child) if ka_child else None
    read.ebay = AdSearchRead.model_validate(ebay_child) if ebay_child else None
    read.mydealz = DealWatchRead.model_validate(watch) if watch else None
    read.ad_count = ad_count
    read.deal_count = deal_count
    read.last_checked_at = max(known) if known else None
    return read
