"""Datenbank-Engine, Session-Abhaengigkeiten und Initialisierung."""

import json
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config, get_app_root

# Datenverzeichnis anlegen, falls nicht vorhanden
(get_app_root() / "data").mkdir(exist_ok=True)

# Datenbank-Engine erstellen
_is_sqlite = config.database_url.startswith("sqlite")
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        session.commit()


def get_db_session():
    """Liefert eine DB-Session; bei SQLite mit aktiviertem foreign_keys-Pragma."""
    with Session(db_engine) as session:
        if _is_sqlite:
            session.execute(text("PRAGMA foreign_keys=ON"))
        yield session


def get_user_db_session(current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """DB-Session im User-Kontext (JWT-Claims fuer Postgres-Sessions)."""
    with Session(db_engine) as session:
        if _is_sqlite:
            session.execute(text("PRAGMA foreign_keys=ON"))
        else:
            # JWT-`sub` fuer RLS; kein set_config('role') (entspricht SET ROLE, oft fehlerhaft).
            claims = json.dumps(
                {
                    "sub": current_user.tenant_id,
                    "role": "authenticated",
                    "app_metadata": current_user.app_metadata,
                },
                default=str,
                allow_nan=False,
            )
            session.execute(
                text("SELECT set_config('request.jwt.claims', :claims, true)"),
                {"claims": claims},
            )
        yield session


# Abhängigkeit für FastAPI
DbSession = Annotated[Session, Depends(get_db_session)]
UserDbSession = Annotated[Session, Depends(get_user_db_session)]
