from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.db import DbSession
from app.models.adsearch import AdSearch, AdSearchCreate, AdSearchRead, AdSearchUpdate

router = APIRouter(prefix="/adsearches", tags=["AdSearches"])


@router.get("/", response_model=list[AdSearchRead])
def list_adsearches(session: DbSession):
    """
    Returns all ad searches (Suchaufträge).
    """
    return session.exec(select(AdSearch)).all()


@router.get("/{adsearch_id}", response_model=AdSearchRead)
def get_adsearch(adsearch_id: int, session: DbSession):
    """
    Returns a specific ad search (Suchauftrag).

    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    return adsearch


@router.post("/", response_model=AdSearchRead, status_code=201)
def create_adsearch(data: AdSearchCreate, session: DbSession):
    """
    Create a new ad search (Suchauftrag)
    """
    adsearch = AdSearch.model_validate(data)

    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.patch("/{adsearch_id}", response_model=AdSearchRead)
def update_adsearch(adsearch_id: int, data: AdSearchUpdate, session: DbSession):
    """
    Update an existing ad search (Suchauftrag)

    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(adsearch, key, value)

    session.commit()
    session.refresh(adsearch)

    return adsearch


@router.delete("/{adsearch_id}", status_code=204)
def delete_adsearch(adsearch_id: int, session: DbSession):
    """
    Delete an ad search (Suchauftrag)

    If the given ID does not exist, an error 404 is thrown.
    """
    adsearch = session.get(AdSearch, adsearch_id)

    if not adsearch:
        raise HTTPException(status_code=404, detail="AdSearch not found")

    session.delete(adsearch)
    session.commit()
