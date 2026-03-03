from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.db import DbSession
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: DbSession):
    return session.exec(select(AdSearch)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(adsearch_id: int, session: DbSession):
    adsearch = session.get(AdSearch, adsearch_id)
    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")
    return adsearch


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(data: AdSearchCreate, session: DbSession):
    adsearch = AdSearch.model_validate(data)
    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)
    return adsearch


@router.delete("/{adsearch_id}", status_code=204)
def delete_adsearch(adsearch_id: int, session: DbSession):
    adsearch = session.get(AdSearch, adsearch_id)
    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")
    session.delete(adsearch)
    session.commit()
