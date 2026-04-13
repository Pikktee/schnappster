"""API-Routen für Anzeigen."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.core.auth import CurrentUser, get_current_user
from app.core.db import UserDbSession
from app.models.ad import Ad, AdRead

router = APIRouter(prefix="/ads", tags=["Ads"])


# --------------
# --- Routen ---
# --------------
@router.get("/")
def list_ads(
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    adsearch_id: int | None = None,
    is_analyzed: bool | None = None,
    min_score: int | None = None,
    sort: str = "date",
    limit: int = 24,
    offset: int = 0,
):
    """Gibt paginierte Anzeigen mit optionalen Filtern
    (adsearch_id, is_analyzed, min_score) und Sortierung zurück.
    """
    query = select(Ad).where(Ad.owner_id == current_user.user_id)

    if adsearch_id is not None:
        query = query.where(Ad.adsearch_id == adsearch_id)
    if is_analyzed is not None:
        query = query.where(Ad.is_analyzed == is_analyzed)
    if min_score is not None and min_score > 0:
        query = query.where(col(Ad.bargain_score) >= min_score)

    total = session.exec(select(func.count()).select_from(query.subquery())).one()

    order = {
        "date": col(Ad.first_seen_at).desc(),
        "price-asc": col(Ad.price).asc(),
        "price-desc": col(Ad.price).desc(),
        "score-desc": col(Ad.bargain_score).desc(),
    }
    query = query.order_by(order.get(sort, col(Ad.first_seen_at).desc()))
    query = query.offset(offset).limit(min(limit, 100))

    items = session.exec(query).all()
    return {"items": [AdRead.model_validate(ad) for ad in items], "total": total}


@router.get("/{ad_id}", response_model=AdRead)
def get_ad(
    ad_id: int,
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt eine Anzeige anhand der ID zurück; 404 wenn nicht gefunden."""
    ad = session.exec(
        select(Ad).where(Ad.id == ad_id, Ad.owner_id == current_user.user_id)
    ).first()

    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    return ad
