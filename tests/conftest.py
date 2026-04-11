"""Gemeinsame Test-Fixtures für Schnappster-Tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_db_session, get_user_db_session
from app.models.ad import Ad
from app.models.adsearch import AdSearch
from app.models.logs_aianalysis import AIAnalysisLog
from app.routes import api_router

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(name="engine")
def engine_fixture():
    """Erstellt eine SQLite-In-Memory-Datenbank für Tests."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    return test_engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Erstellt eine Datenbank-Session für Tests."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """Erstellt einen FastAPI-Test-Client mit Testdatenbank."""
    test_app = FastAPI()
    test_app.include_router(api_router)

    def override_get_db_session():
        yield session

    def override_get_current_user():
        return CurrentUser(
            id=TEST_USER_ID,
            email="test@example.com",
            app_metadata={"role": "admin", "providers": ["email"]},
            user_metadata={"name": "Test User"},
            identities=[],
            access_token="test-token",
        )

    test_app.dependency_overrides[get_db_session] = override_get_db_session
    test_app.dependency_overrides[get_user_db_session] = override_get_db_session
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def sample_adsearch(session):
    """Erstellt einen Beispiel-Suchauftrag für Tests."""
    adsearch = AdSearch(
        owner_id=TEST_USER_ID,
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
    """Erstellt Beispiel-Anzeigen für Tests."""
    ads = [
        Ad(
            owner_id=TEST_USER_ID,
            external_id="1001",
            title="Rode PodMic",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic/1001",
            price=55.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_name="Anna",
            seller_rating=2,
            seller_type="Privat",
            bargain_score=7.0,
            ai_summary="Gutes Angebot",
            ai_reasoning="Unter dem Durchschnitt",
            is_analyzed=True,
            image_urls="https://img.kleinanzeigen.de/test1.jpg,https://img.kleinanzeigen.de/test2.jpg",
        ),
        Ad(
            owner_id=TEST_USER_ID,
            external_id="1002",
            title="Rode PodMic USB",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic-usb/1002",
            price=80.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_name="Bert",
            seller_rating=1,
            seller_type="Privat",
            is_analyzed=False,
            image_urls="https://img.kleinanzeigen.de/test3.jpg",
        ),
        Ad(
            owner_id=TEST_USER_ID,
            external_id="1003",
            title="Rode PodMic defekt",
            url="https://www.kleinanzeigen.de/s-anzeige/rode-podmic-defekt/1003",
            price=15.0,
            postal_code="60325",
            city="Frankfurt",
            adsearch_id=sample_adsearch.id,
            seller_name="Claudia",
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


@pytest.fixture
def sample_ai_analysis_log(session, sample_ads, sample_adsearch):
    """KI-Analyse-Log für die erste Beispielanzeige (inkl. Suchauftrag)."""
    ad = sample_ads[0]
    log = AIAnalysisLog(
        ad_id=ad.id,
        adsearch_id=sample_adsearch.id,
        ad_title=ad.title,
        score=7.0,
        ai_summary="Test summary",
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
