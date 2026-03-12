"""Datenbank-Engine, Session-Abhängigkeit und Initialisierung."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.config import config, get_app_root

# Datenverzeichnis anlegen, falls nicht vorhanden
(get_app_root() / "data").mkdir(exist_ok=True)

# Datenbank-Engine erstellen
db_engine = create_engine(config.database_url, echo=False, connect_args={})


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        session.commit()


def get_db_session():
    """Liefert eine DB-Session mit aktiviertem SQLite-Pragma foreign_keys."""
    with Session(db_engine) as session:
        # SQLite braucht foreign_keys=ON für CASCADE/SET NULL
        session.execute(text("PRAGMA foreign_keys=ON"))
        yield session


# Abhängigkeit für FastAPI
DbSession = Annotated[Session, Depends(get_db_session)]
