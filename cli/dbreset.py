"""Datenbank zurücksetzen (nur Schema löschen und neu anlegen).

Verwendung:
    uv run dbreset
"""

import logging

from sqlmodel import SQLModel

import app.models  # noqa: F401 — SQLModel-Metadaten registrieren
from app.core import db_engine, init_db, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Entfernt alle Tabellen und legt das Schema neu an."""
    setup_logging()
    SQLModel.metadata.drop_all(db_engine)
    init_db()
    logger.info("Database schema recreated")
