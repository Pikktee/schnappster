"""Shared test fixtures for Schnappster tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.routes import api_router
from app.core.db import get_db_session
from app.models.ad import Ad
from app.models.adsearch import AdSearch


@pytest.fixture(name="engine")
def engine_fixture():
    """Create an in-memory SQLite database for testing."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """Create a FastAPI test client with test database."""
    test_app = FastAPI()
    test_app.include_router(api_router)

    def override_get_db_session():
        yield session

    test_app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def sample_adsearch(session):
    """Create a sample AdSearch for testing."""
    adsearch = AdSearch(
        name="Test Search",
        url="https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250",
        min_price=20.0,
        max_price=200.0,
        blacklist_keywords="defekt,bastler",
        is_active=True,
    )
    session.add(adsearch)
    session.commit()
    session.refresh(adsearch)
    return adsearch


@pytest.fixture
def sample_ads(session, sample_adsearch):
    """Create sample Ads for testing."""
    ads = [
        Ad(
            external_id="1001",
            title="Rode PodMic",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic/1001",
            price=55.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_rating=2,
            seller_type="Privat",
            bargain_score=7.0,
            ai_summary="Gutes Angebot",
            ai_reasoning="Unter dem Durchschnitt",
            is_analyzed=True,
            image_urls="https://img.kleinanzeigen.de/test1.jpg,https://img.kleinanzeigen.de/test2.jpg",
        ),
        Ad(
            external_id="1002",
            title="Rode PodMic USB",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic-usb/1002",
            price=80.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_rating=1,
            seller_type="Privat",
            is_analyzed=False,
            image_urls="https://img.kleinanzeigen.de/test3.jpg",
        ),
        Ad(
            external_id="1003",
            title="Rode PodMic defekt",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic-defekt/1003",
            price=15.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_rating=0,
            seller_type="Gewerblich",
            is_analyzed=False,
        ),
    ]
    for ad in ads:
        session.add(ad)
    session.commit()
    for ad in ads:
        session.refresh(ad)
    return ads
