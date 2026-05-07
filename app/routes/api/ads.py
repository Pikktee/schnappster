"""API-Routen für Anzeigen."""

from fastapi import APIRouter, Depends, HTTPException, Query
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
    min_score: int | None = Query(default=None, ge=0, le=10),
    sort: str = "date",
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Gibt paginierte Anzeigen mit optionalen Filtern
    (adsearch_id, is_analyzed, min_score) und Sortierung zurück.
    """
    filters = [Ad.owner_id == current_user.user_id]

    if adsearch_id is not None:
        filters.append(Ad.adsearch_id == adsearch_id)
    if is_analyzed is not None:
        filters.append(Ad.is_analyzed == is_analyzed)
    if min_score is not None and min_score > 0:
        filters.append(col(Ad.bargain_score) >= min_score)

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
    session: UserDbSession,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
):
    """Gibt eine Anzeige anhand der ID zurück; 404 wenn nicht gefunden."""
    ad = session.exec(select(Ad).where(Ad.id == ad_id, Ad.owner_id == current_user.user_id)).first()

    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    result = AdRead.model_validate(ad)
    session.rollback()
    return result
