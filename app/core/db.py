"""Datenbank-Engine, Session-Abhaengigkeiten und Initialisierung."""

import threading
from typing import Annotated

from fastapi import Depends
from sqlalchemy import NullPool
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config
from app.core.debug_runtime import write_debug_log

_connect_args: dict[str, object] = {
    "connect_timeout": config.db_connect_timeout,
    # prepare_threshold=None: psycopg3 darf keine server-seitigen prepared statements nutzen.
    # Supabase Transaction-Mode-Pooler (Supavisor) routet Queries an wechselnde Backends —
    # prepared statements sind dort nicht portabel und loesen DuplicatePreparedStatement aus.
    "prepare_threshold": None,
}

# --- API-Engine: QueuePool fuer schnelle, kurzlebige Requests ---
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_connect_args,
    pool_size=config.db_pool_size,
    max_overflow=config.db_max_overflow,
    pool_timeout=config.db_pool_timeout,
    pool_recycle=config.db_pool_recycle,
    pool_pre_ping=True,
    pool_use_lifo=True,
)

# --- Background-Engine: NullPool fuer Scraper/Analyzer, die Sessions minutenlang halten ---
# Separate Engine, damit lang laufende Hintergrund-Jobs nie den API-Pool blockieren.
bg_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_connect_args,
    poolclass=NullPool,
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
    """DB-Session mit Auth-Guard — stellt sicher, dass nur authentifizierte User zugreifen.

    Alle Routen filtern bereits auf Anwendungsebene nach ``owner_id``; Postgres-RLS
    (``set_config``) ist daher nicht noetig und wuerde den Transaction-Mode-Pooler
    von Supabase blockieren (Session-State ist dort nicht portabel).
    """
    with Session(db_engine) as session:
        # region agent log
        write_debug_log(
            run_id="post-fix",
            hypothesis_id="H2",
            location="app/core/db.py:get_user_db_session",
            message="opened authenticated db session",
            data={
                "thread_id": threading.get_ident(),
                "has_user": bool(current_user.id),
                "pool_status": db_engine.pool.status(),
            },
        )
        # endregion
        yield session
        # region agent log
        write_debug_log(
            run_id="post-fix",
            hypothesis_id="H2",
            location="app/core/db.py:get_user_db_session",
            message="closing authenticated db session",
            data={
                "thread_id": threading.get_ident(),
                "has_user": bool(current_user.id),
                "pool_status": db_engine.pool.status(),
            },
        )
        # endregion


# Abhängigkeit für FastAPI
DbSession = Annotated[Session, Depends(get_db_session)]
UserDbSession = Annotated[Session, Depends(get_user_db_session)]
