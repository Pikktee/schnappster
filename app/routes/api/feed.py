"""API-Route für den Ergebnis-Stream der Startseite.

Mischt die drei Quellen (Anzeigen von Kleinanzeigen/eBay, MyDealz-Deals, Preisänderungen der
Preis-Alarme) chronologisch. ``min_score`` filtert nur die KI-bewerteten Anzeigen — Deals und
Preis-Ereignisse bleiben sichtbar, sie haben eigene Relevanzkriterien. Von den Preis-Alarmen
erscheinen nur Preisänderungen, die deren Alarm-Kriterien erfüllen (Preisrückgang; mit Zielpreis
erst ab dessen Erreichen) — der Basis-Messpunkt beim Anlegen und Preisanstiege sind kein Ergebnis.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.auth import CurrentUser, get_current_user
from app.core.db import SessionDep
from app.models.ad import Ad, AdRead
from app.models.adsearch import AdSearch
from app.models.deal_watch import Deal, DealRead, DealWatch
from app.models.feed import (
    FEED_TYPE_AD,
    FEED_TYPE_DEAL,
    FEED_TYPE_PRICE,
    FeedItem,
    FeedPage,
    FeedPriceEvent,
)
from app.models.price_watch import PricePoint, PriceWatch
from app.services.deal_watch import compute_heating_velocity

router = APIRouter(prefix="/feed", tags=["Feed"])

_SORTS = {"date", "price-asc", "price-desc", "score-desc"}


@router.get("/", response_model=FeedPage)
def get_feed(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str = "all",
    min_score: int | None = Query(default=None, ge=0, le=10),
    search_order_id: int | None = None,
    sort: str = "date",
):
    """Liefert eine Seite des gemischten Ergebnis-Streams (neueste zuerst)."""
    if sort not in _SORTS:
        sort = "date"
    owner = current_user.user_id
    fetch_n = offset + limit
    # Nur die Score-Sortierung ist anzeigen-exklusiv (Deals/Preise haben keinen KI-Score);
    # der Mindest-Score filtert Anzeigen, lässt die anderen Quellen aber im Stream.
    ads_only = sort == "score-desc"

    want_ads = source in ("all", "kleinanzeigen", "ebay")
    want_deals = source in ("all", "mydealz") and not ads_only
    want_prices = source in ("all", "price") and not ads_only and search_order_id is None

    items: list[FeedItem] = []
    total = 0
    if want_ads:
        ad_items, ad_total = _load_ads(
            session, owner, fetch_n, source, min_score, search_order_id, sort
        )
        items += ad_items
        total += ad_total
    if want_deals:
        deal_items, deal_total = _load_deals(session, owner, fetch_n, search_order_id, sort)
        items += deal_items
        total += deal_total
    if want_prices:
        price_items, price_total = _load_price_events(session, owner, fetch_n, sort)
        items += price_items
        total += price_total

    items.sort(key=lambda item: _sort_key(item, sort))
    page = items[offset : offset + limit]
    session.rollback()
    return FeedPage(items=page, total=total)


# -----------------------
# --- Quellen-Loader ---
# -----------------------
def _load_ads(
    session: Session,
    owner: str,
    fetch_n: int,
    source: str,
    min_score: int | None,
    search_order_id: int | None,
    sort: str,
) -> tuple[list[FeedItem], int]:
    filters = [Ad.owner_id == owner]
    if min_score is not None and min_score > 0:
        filters.append(col(Ad.bargain_score) >= min_score)
    # Kleinanzeigen vs. eBay steckt (wie im Frontend-Badge) im URL-Host der Anzeige.
    if source == "ebay":
        filters.append(col(Ad.url).like("%ebay.%"))
    elif source == "kleinanzeigen":
        filters.append(col(Ad.url).not_like("%ebay.%"))
    if search_order_id is not None:
        child_ids = select(AdSearch.id).where(AdSearch.search_order_id == search_order_id)
        filters.append(col(Ad.adsearch_id).in_(child_ids))

    order = {
        "date": col(Ad.first_seen_at).desc(),
        "price-asc": col(Ad.price).asc().nullslast(),
        "price-desc": col(Ad.price).desc().nullslast(),
        "score-desc": col(Ad.bargain_score).desc().nullslast(),
    }[sort]
    total = session.exec(select(func.count(col(Ad.id))).where(*filters)).one()
    ads = session.exec(
        select(Ad).where(*filters).order_by(order, col(Ad.id).desc()).limit(fetch_n)
    ).all()
    items = [
        FeedItem(
            type=FEED_TYPE_AD,
            occurred_at=ad.first_seen_at,
            ad=AdRead.model_validate(ad),
        )
        for ad in ads
    ]
    return items, total


def _load_deals(
    session: Session, owner: str, fetch_n: int, search_order_id: int | None, sort: str
) -> tuple[list[FeedItem], int]:
    filters = [Deal.owner_id == owner]
    if search_order_id is not None:
        watch_ids = select(DealWatch.id).where(DealWatch.search_order_id == search_order_id)
        filters.append(col(Deal.deal_watch_id).in_(watch_ids))

    order = {
        "date": (col(Deal.published_at).desc().nullslast(), col(Deal.first_seen_at).desc()),
        "price-asc": (col(Deal.price).asc().nullslast(),),
        "price-desc": (col(Deal.price).desc().nullslast(),),
        "score-desc": (col(Deal.published_at).desc().nullslast(),),  # unerreichbar (ads_only)
    }[sort]
    total = session.exec(select(func.count(col(Deal.id))).where(*filters)).one()
    deals = session.exec(select(Deal).where(*filters).order_by(*order).limit(fetch_n)).all()

    items = []
    for deal in deals:
        read = DealRead.model_validate(deal)
        read.heating_velocity = compute_heating_velocity(deal)
        items.append(
            FeedItem(type=FEED_TYPE_DEAL, occurred_at=_deal_time(deal), deal=read)
        )
    return items, total


def _load_price_events(
    session: Session, owner: str, fetch_n: int, sort: str
) -> tuple[list[FeedItem], int]:
    """Nur Preisänderungen, die die Alarm-Kriterien ihrer Überwachung erfüllen.

    Lädt die komplette Historie des Nutzers, weil "qualifiziert" vom jeweils vorherigen
    Messpunkt abhängt — die Historie speichert ohnehin nur Änderungen und bleibt klein.
    """
    rows = session.exec(
        select(PricePoint, PriceWatch)
        .join(PriceWatch, col(PricePoint.pricewatch_id) == col(PriceWatch.id))
        .where(PricePoint.owner_id == owner)
        .order_by(col(PricePoint.pricewatch_id), col(PricePoint.id))
    ).all()

    items: list[FeedItem] = []
    previous_by_watch: dict[int, float] = {}
    for point, watch in rows:
        watch_id: int = point.pricewatch_id
        previous = previous_by_watch.get(watch_id)
        previous_by_watch[watch_id] = point.price
        if not _price_event_qualifies(point.price, previous, watch.notify_threshold):
            continue
        items.append(
            FeedItem(
                type=FEED_TYPE_PRICE,
                occurred_at=point.recorded_at,
                price_event=FeedPriceEvent(
                    watch_id=watch_id,
                    watch_name=watch.name,
                    url=watch.url,
                    price=point.price,
                    previous_price=previous,
                    currency=point.currency or watch.currency,
                    recorded_at=point.recorded_at,
                ),
            )
        )

    items.sort(key=lambda item: _sort_key(item, sort))
    return items[:fetch_n], len(items)


# -----------------------
# --- Hilfsfunktionen ---
# -----------------------
def _price_event_qualifies(
    price: float, previous: float | None, threshold: float | None
) -> bool:
    """Alarm-Kriterien eines Preis-Alarms: Preisrückgang, mit Zielpreis erst ab Erreichen.

    Der erste Messpunkt (Baseline beim Anlegen) und Preisanstiege sind kein Ergebnis.
    """
    if previous is None or price >= previous:
        return False
    return threshold is None or price <= threshold


def _deal_time(deal: Deal) -> datetime:
    """Zeitpunkt eines Deals: Veröffentlichung auf MyDealz, sonst unser Erst-Sichten."""
    if deal.published_at:
        return datetime.fromtimestamp(deal.published_at, UTC)
    return deal.first_seen_at


def _naive(value: datetime) -> datetime:
    """Zeitzonen-normalisiert für den Misch-Sort (SQLite liefert naive Werte)."""
    return value.replace(tzinfo=None) if value.tzinfo else value


def _sort_key(item: FeedItem, sort: str) -> tuple:
    """Sortierschlüssel über Quellen hinweg (None-Preise/-Scores ans Ende)."""
    if sort == "price-asc" or sort == "price-desc":
        price = (
            item.ad.price
            if item.ad
            else item.deal.price
            if item.deal
            else item.price_event.price
            if item.price_event
            else None
        )
        if sort == "price-asc":
            return (price is None, price if price is not None else 0.0)
        return (price is None, -(price if price is not None else 0.0))
    if sort == "score-desc":
        score = item.ad.bargain_score if item.ad else None
        return (score is None, -(score if score is not None else 0.0))
    return (-_naive(item.occurred_at).timestamp(),)
