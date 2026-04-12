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
_is_postgres = config.database_url.startswith("postgresql")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
if _is_postgres:
    # Verhindert haengende Requests, wenn externe DB kurzfristig nicht erreichbar ist.
    _connect_args = {**_connect_args, "connect_timeout": 5}
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_connect_args,
)


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        if _is_sqlite:
            _ensure_user_settings_columns(session)
            _drop_obsolete_user_settings_columns_sqlite(session)
        session.commit()


def _column_exists_sqlite(session: Session, table: str, column: str) -> bool:
    rows = session.execute(text(f"PRAGMA table_info({table})")).all()
    return any(len(row) > 1 and row[1] == column for row in rows)


def _ensure_user_settings_columns(session: Session) -> None:
    """Sichert nachgezogene user_settings-Spalten fuer bestehende Datenbanken."""
    table_name = "user_settings"
    column_name = "display_name_user_set"
    if _column_exists_sqlite(session, table_name, column_name):
        return
    session.execute(
        text(
            "ALTER TABLE user_settings "
            "ADD COLUMN display_name_user_set BOOLEAN NOT NULL DEFAULT 0"
        )
    )


def _drop_obsolete_user_settings_columns_sqlite(session: Session) -> None:
    """Entfernt nicht mehr genutzte Spalten (Feature entfernt, kein Alembic)."""
    table_name = "user_settings"
    column_name = "notify_email"
    if not _column_exists_sqlite(session, table_name, column_name):
        return
    session.execute(text(f"ALTER TABLE {table_name} DROP COLUMN {column_name}"))


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
