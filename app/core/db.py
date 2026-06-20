"""Datenbank-Engine, Session-Abhaengigkeit und Initialisierung."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import config

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
    """Alle Tabellen anlegen. Schemaaenderungen laufen ueber `uv run dbreset`."""
    SQLModel.metadata.create_all(db_engine)


def get_session():
    """Liefert eine DB-Session pro Request."""
    with Session(db_engine) as session:
        yield session


# Abhängigkeit für FastAPI
SessionDep = Annotated[Session, Depends(get_session)]
