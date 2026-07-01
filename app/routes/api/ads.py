"""API-Routen für Anzeigen."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, func, select

from app.core.auth import CurrentUser, get_current_user
from app.core.db import SessionDep
from app.models.ad import Ad, AdRead, MarketReference, NegotiationMessage, SoldComp
from app.services.ai import AIService
from app.services.price_reference import EbayBlockedError, get_ebay_sold_reference

router = APIRouter(prefix="/ads", tags=["Ads"])

# Anzeigentitel auf einen brauchbaren eBay-Suchbegriff kürzen.
_MARKET_QUERY_MAX_LEN = 80


# --------------
# --- Routen ---
# --------------
@router.get("/")
def list_ads(
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    adsearch_id: int | None = None,
    is_analyzed: bool | None = None,
    min_score: int | None = Query(default=None, ge=0, le=10),
    external_id: str | None = None,
    sort: str = "date",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Gibt paginierte Anzeigen mit optionalen Filtern
    (adsearch_id, is_analyzed, min_score, external_id) und Sortierung zurück.
    """
    filters = [Ad.owner_id == current_user.user_id]

    if adsearch_id is not None:
        filters.append(Ad.adsearch_id == adsearch_id)
    if is_analyzed is not None:
        filters.append(Ad.is_analyzed == is_analyzed)
    if min_score is not None and min_score > 0:
        filters.append(col(Ad.bargain_score) >= min_score)
    if external_id is not None:
        filters.append(Ad.external_id == external_id)

    total = session.exec(select(func.count(Ad.id)).where(*filters)).one()

    order = {
        "date": col(Ad.first_seen_at).desc(),
        "price-asc": col(Ad.price).asc(),
        "price-desc": col(Ad.price).desc(),
        "score-desc": col(Ad.bargain_score).desc(),
    }
    query = (
        select(Ad)
        .where(*filters)
        .order_by(order.get(sort, col(Ad.first_seen_at).desc()), col(Ad.id).desc())
        .offset(offset)
        .limit(limit)
    )

    items = session.exec(query).all()
    result = {"items": [AdRead.model_validate(ad) for ad in items], "total": total}
    session.rollback()
    return result


@router.get("/{ad_id}", response_model=AdRead)
def get_ad(
    ad_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt eine Anzeige anhand der ID zurück; 404 wenn nicht gefunden."""
    ad = session.exec(select(Ad).where(Ad.id == ad_id, Ad.owner_id == current_user.user_id)).first()

    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    result = AdRead.model_validate(ad)
    session.rollback()
    return result


@router.post("/{ad_id}/negotiation-message", response_model=NegotiationMessage)
def create_negotiation_message(
    ad_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Erzeugt per KI eine Verhandlungsnachricht + faires Gegenangebot für die Anzeige."""
    ad = session.exec(select(Ad).where(Ad.id == ad_id, Ad.owner_id == current_user.user_id)).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    try:
        service = AIService(session)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        result = service.generate_negotiation_message(ad)
    except Exception as exc:  # noqa: BLE001 — als klare HTTP-Antwort weitergeben
        raise HTTPException(
            status_code=502,
            detail=f"Verhandlungsnachricht konnte nicht erzeugt werden: {exc}",
        ) from exc

    return NegotiationMessage(**result)


@router.post("/{ad_id}/market-reference", response_model=MarketReference)
def market_reference(
    ad_id: int,
    session: SessionDep,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Ermittelt den Marktwert aus echten eBay-Verkäufen (Median + Spanne) zur Anzeige."""
    ad = session.exec(select(Ad).where(Ad.id == ad_id, Ad.owner_id == current_user.user_id)).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")
    query = (ad.title or "").strip()[:_MARKET_QUERY_MAX_LEN]
    session.rollback()  # Read-Transaktion vor dem externen Abruf schließen

    if not query:
        return MarketReference(query="")

    try:
        reference = get_ebay_sold_reference(query)
    except EbayBlockedError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "eBay hat den Abruf blockiert oder war nicht erreichbar "
                "(in Prod ggf. Proxy nötig)."
            ),
        ) from exc

    if reference is None:
        return MarketReference(query=query)

    return MarketReference(
        query=reference.query,
        currency=reference.currency,
        median=reference.median,
        low=reference.low,
        high=reference.high,
        count=reference.count,
        comps=[
            SoldComp(
                title=listing.title,
                price=listing.price,
                sold_date=listing.sold_date,
                condition=listing.condition,
            )
            for listing in reference.listings[:8]
        ],
    )
