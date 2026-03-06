from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.db import DbSession
from app.models.ad import Ad, AdRead

router = APIRouter(prefix="/ads", tags=["Ads"])


@router.get("/", response_model=list[AdRead])
def list_ads(session: DbSession, adsearch_id: int | None = None, is_analyzed: bool | None = None):
    query = select(Ad)

    if adsearch_id is not None:
        query = query.where(Ad.adsearch_id == adsearch_id)
    if is_analyzed is not None:
        query = query.where(Ad.is_analyzed == is_analyzed)

    return session.exec(query).all()


@router.get("/{ad_id}", response_model=AdRead)
def get_ad(ad_id: int, session: DbSession):
    ad = session.get(Ad, ad_id)

    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    return ad
