"""Tests fuer die eigene JWT-Auth (Token, Dependency, Freischaltung)."""

import pytest
from fastapi import HTTPException

from app.core import auth
from app.core.security import hash_password, validate_password_strength, verify_password
from app.models.user import User


def test_password_hash_roundtrip():
    """Hash + Verify funktioniert, falsches Passwort schlaegt fehl."""
    h = hash_password("Geheim12!")
    assert verify_password("Geheim12!", h)
    assert not verify_password("falsch", h)


def test_password_policy_rejects_weak():
    """Schwaches Passwort wirft ValueError, starkes nicht."""
    with pytest.raises(ValueError):
        validate_password_strength("kurz")
    validate_password_strength("Geheim12!")


def test_access_token_roundtrip():
    """Ein erzeugtes Token enthaelt sub/role und ist dekodierbar."""
    user = User(id="abc", email="a@b.de", password_hash="x", role="admin", is_active=True)
    token = auth.create_access_token(user)
    payload = auth._decode_token(token)
    assert payload["sub"] == "abc"
    assert payload["role"] == "admin"


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        auth._decode_token("nicht.gueltig.token")
    assert exc.value.status_code == 401


def test_get_current_user_rejects_inactive(session):
    """Inaktiver User wird trotz gueltigem Token mit 401 abgewiesen."""
    user = User(
        id="u1", email="u1@test.de", password_hash="x", role="user", is_active=False
    )
    session.add(user)
    session.commit()
    token = auth.create_access_token(user)
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(authorization=f"Bearer {token}", session=session)
    assert exc.value.status_code == 401


def test_get_current_user_accepts_active(session):
    """Aktiver User wird korrekt aufgeloest."""
    user = User(
        id="u2", email="u2@test.de", password_hash="x", role="admin", is_active=True
    )
    session.add(user)
    session.commit()
    token = auth.create_access_token(user)
    current = auth.get_current_user(authorization=f"Bearer {token}", session=session)
    assert current.user_id == "u2"
    assert current.role == "admin"


def test_missing_authorization_raises_401():
    with pytest.raises(HTTPException) as exc:
        auth._extract_bearer_token(None)
    assert exc.value.status_code == 401
