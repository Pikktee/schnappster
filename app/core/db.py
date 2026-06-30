"""Datenbank-Engine, Session-Abhaengigkeit und Initialisierung."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event, inspect
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import config

logger = logging.getLogger(__name__)

# Additive Spalten, die in bestehenden Tabellen fehlen koennen (kein Alembic).
# Format: (Tabelle, Spalte, SQL-Definition fuer ADD COLUMN). Nur additiv, idempotent.
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("user_settings", "notify_price_telegram", "BOOLEAN NOT NULL DEFAULT 0"),
]

_SQLITE_PREFIX = "sqlite:///"
_is_sqlite = config.database_url.startswith("sqlite")


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Legt den Ordner der SQLite-Datei an — SQLite erstellt nur die Datei selbst."""
    if not database_url.startswith(_SQLITE_PREFIX):
        return
    raw_path = database_url[len(_SQLITE_PREFIX) :]
    if not raw_path or raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(config.database_url)

db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


if _is_sqlite:

    @event.listens_for(db_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        """WAL fuer parallele Leser, FK-Enforcement, kurze Lock-Wartezeit, schnelleres Commit."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def init_db() -> None:
    """Alle Tabellen anlegen; fehlende additive Spalten in bestehenden Tabellen ergaenzen.

    Strukturelle Schemaaenderungen laufen weiterhin ueber `uv run dbreset`; nur
    rueckwaertskompatible Spaltenzusaetze werden hier ohne Datenverlust nachgezogen.
    """
    SQLModel.metadata.create_all(db_engine)
    _apply_additive_columns()


def _apply_additive_columns() -> None:
    """Ergaenzt fehlende Spalten aus `_ADDITIVE_COLUMNS` (idempotent, ohne Datenverlust)."""
    inspector = inspect(db_engine)
    existing_tables = set(inspector.get_table_names())
    with db_engine.begin() as conn:
        for table, column, ddl in _ADDITIVE_COLUMNS:
            if table not in existing_tables:
                continue
            if column in {col["name"] for col in inspector.get_columns(table)}:
                continue
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
            logger.info("Added missing column %s.%s", table, column)


def get_session():
    """Liefert eine DB-Session pro Request."""
    with Session(db_engine) as session:
        yield session


# Abhängigkeit für FastAPI
SessionDep = Annotated[Session, Depends(get_session)]
