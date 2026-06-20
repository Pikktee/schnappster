"""Gemeinsame Test-Fixtures für Schnappster-Tests (SQLite in-memory)."""

from __future__ import annotations

import os


# ``app.core`` baut ``Config()`` beim Import — DATABASE_URL und JWT_SECRET muessen gesetzt sein.
def _ensure_process_env() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("JWT_SECRET", "test-secret-key-which-is-long-enough-32b")


_ensure_process_env()

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

import app.models  # noqa: E402, F401 — Metadaten registrieren
from app.core.auth import CurrentUser, get_current_user  # noqa: E402
from app.core.db import get_session  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.ad import Ad  # noqa: E402
from app.models.adsearch import AdSearch  # noqa: E402
from app.models.logs_aianalysis import AIAnalysisLog  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routes import api_router  # noqa: E402

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(name="engine")
def engine_fixture():
    """Frische In-Memory-SQLite pro Test (eine geteilte Verbindung via StaticPool)."""
    eng = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    """Eine Datenbank-Session für einen Test."""
    with Session(engine) as session:
        yield session


def _build_test_app(session) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(api_router)

    def override_get_session():
        yield session

    test_app.dependency_overrides[get_session] = override_get_session
    return test_app


@pytest.fixture(name="client")
def client_fixture(session):
    """Test-Client mit Admin-User-Override (umgeht die echte Token-Pruefung)."""
    test_app = _build_test_app(session)

    def override_get_current_user():
        return CurrentUser(id=TEST_USER_ID, email="test@example.com", role="admin")

    test_app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(test_app) as client:
        yield client


@pytest.fixture(name="api_client")
def api_client_fixture(session):
    """Test-Client mit ECHTER Auth (nur die DB-Session ist gemockt) — fuer Auth-/Admin-Tests."""
    test_app = _build_test_app(session)
    with TestClient(test_app) as client:
        yield client


def make_user(
    session,
    *,
    email: str,
    password: str = "Passwort1!",
    role: str = "user",
    is_active: bool = True,
) -> User:
    """Legt einen Benutzer mit gehashtem Passwort an."""
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


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
