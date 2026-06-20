"""Admin-Benutzer anlegen oder aktualisieren.

Verwendung:
    uv run createadmin                                # nutzt ADMIN_EMAIL / ADMIN_PASSWORD
    uv run createadmin admin@example.com              # Passwort interaktiv abfragen
    uv run createadmin admin@example.com 'GeheimPW1!' # beides direkt
"""

import getpass
import logging
import sys

from sqlmodel import Session, select

import app.models  # noqa: F401 — SQLModel-Metadaten registrieren
from app.core import config, db_engine, init_db, setup_logging
from app.core.security import hash_password, validate_password_strength
from app.models.user import User, normalize_email

logger = logging.getLogger(__name__)


def main() -> None:
    """Legt einen freigeschalteten Admin an oder aktualisiert Passwort/Rolle eines bestehenden."""
    setup_logging()
    init_db()

    args = sys.argv[1:]
    email_raw = args[0] if len(args) > 0 else (config.admin_email or input("Admin-E-Mail: "))
    password = args[1] if len(args) > 1 else config.admin_password
    if not password:
        password = getpass.getpass("Passwort: ")

    try:
        email = normalize_email(email_raw)
        validate_password_strength(password)
    except ValueError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    with Session(db_engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None:
            user = User(email=email, password_hash=hash_password(password), role="admin")
            action = "angelegt"
        else:
            user.password_hash = hash_password(password)
            action = "aktualisiert"
        user.role = "admin"
        user.is_active = True
        session.add(user)
        session.commit()

    logger.info("Admin %s: %s", action, email)
