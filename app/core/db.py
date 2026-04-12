"""Datenbank-Engine, Session-Abhaengigkeiten und Initialisierung."""

import json
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config

_connect_args: dict[str, object] = {"connect_timeout": 5}
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_connect_args,
)


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        _drop_obsolete_user_settings_columns_postgres(session)
        session.commit()


# Aus dem Modell entfernt; alte DBs koennen NOT NULL-Spalten haben, die INSERTs ohne Wert brechen.
_OBSOLETE_USER_SETTINGS_COLUMNS: tuple[str, ...] = ("notify_email", "notify_mode")


def _drop_obsolete_user_settings_columns_postgres(session: Session) -> None:
    """Entfernt Legacy-Spalten, die nicht mehr im SQLModel stehen (NOT NULL blockierte INSERTs)."""
    for column_name in _OBSOLETE_USER_SETTINGS_COLUMNS:
        session.execute(text(f"ALTER TABLE user_settings DROP COLUMN IF EXISTS {column_name}"))


def get_db_session():
    """Liefert eine DB-Session."""
    with Session(db_engine) as session:
        yield session


def get_user_db_session(current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """DB-Session im User-Kontext (JWT-Claims fuer Postgres-Sessions / RLS)."""
    with Session(db_engine) as session:
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
