"""End-to-End-Tests: Registrierung/Freischaltung, Login, Owner-Isolation, Admin-Verwaltung."""

from app.core.security import hash_password
from app.models.adsearch import AdSearch
from app.models.user import User


def _add_user(session, email, password="Passwort1!", role="user", is_active=True):
    user = User(
        email=email, password_hash=hash_password(password), role=role, is_active=is_active
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _login(api_client, email, password="Passwort1!"):
    return api_client.post("/auth/login", json={"email": email, "password": password})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_inactive_and_login_blocked(api_client):
    """Registrierung legt inaktives Konto an; Login bleibt bis zur Freischaltung gesperrt."""
    r = api_client.post("/auth/register", json={"email": "neu@test.de", "password": "Passwort1!"})
    assert r.status_code == 201
    r = _login(api_client, "neu@test.de")
    assert r.status_code == 403


def test_register_weak_password_422(api_client):
    r = api_client.post("/auth/register", json={"email": "x@test.de", "password": "kurz"})
    assert r.status_code == 422


def test_register_duplicate_email_409(api_client, session):
    _add_user(session, "dup@test.de")
    r = api_client.post("/auth/register", json={"email": "dup@test.de", "password": "Passwort1!"})
    assert r.status_code == 409


def test_login_wrong_password_401(api_client, session):
    _add_user(session, "a@test.de")
    r = _login(api_client, "a@test.de", "Falsch123!")
    assert r.status_code == 401


def test_login_success_returns_token(api_client, session):
    _add_user(session, "a@test.de")
    r = _login(api_client, "a@test.de")
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_owner_isolation_between_users(api_client, session):
    """Ein User sieht keine Suchauftraege eines anderen Users."""
    user_a = _add_user(session, "a@test.de")
    _add_user(session, "b@test.de")
    session.add(AdSearch(owner_id=user_a.id, name="A-Suche", url="https://www.kleinanzeigen.de/s-x"))
    session.commit()

    tok_b = _login(api_client, "b@test.de").json()["access_token"]
    r = api_client.get("/adsearches/", headers=_auth(tok_b))
    assert r.status_code == 200
    assert r.json() == []

    tok_a = _login(api_client, "a@test.de").json()["access_token"]
    r = api_client.get("/adsearches/", headers=_auth(tok_a))
    assert len(r.json()) == 1


def test_admin_endpoints_forbidden_for_normal_user(api_client, session):
    _add_user(session, "u@test.de", role="user")
    tok = _login(api_client, "u@test.de").json()["access_token"]
    assert api_client.get("/admin/users/", headers=_auth(tok)).status_code == 403


def test_admin_can_activate_user(api_client, session):
    """Admin schaltet einen registrierten User frei; danach klappt der Login."""
    _add_user(session, "admin@test.de", role="admin")
    target = _add_user(session, "wait@test.de", role="user", is_active=False)
    tok = _login(api_client, "admin@test.de").json()["access_token"]

    assert _login(api_client, "wait@test.de").status_code == 403
    r = api_client.patch(
        f"/admin/users/{target.id}", headers=_auth(tok), json={"is_active": True}
    )
    assert r.status_code == 200 and r.json()["is_active"] is True
    assert _login(api_client, "wait@test.de").status_code == 200


def test_admin_create_and_delete_user(api_client, session):
    _add_user(session, "admin@test.de", role="admin")
    tok = _login(api_client, "admin@test.de").json()["access_token"]

    r = api_client.post(
        "/admin/users/",
        headers=_auth(tok),
        json={"email": "made@test.de", "password": "Passwort1!", "role": "user"},
    )
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert _login(api_client, "made@test.de").status_code == 200

    r = api_client.delete(f"/admin/users/{new_id}", headers=_auth(tok))
    assert r.status_code == 204
    assert session.get(User, new_id) is None


def test_admin_cannot_delete_last_admin(api_client, session):
    admin = _add_user(session, "admin@test.de", role="admin")
    tok = _login(api_client, "admin@test.de").json()["access_token"]
    # Eigenes Konto: ueber /users/me, nicht hier -> 400
    r = api_client.delete(f"/admin/users/{admin.id}", headers=_auth(tok))
    assert r.status_code == 400
