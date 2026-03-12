"""Datenbank zurücksetzen (nur Schema löschen und neu anlegen).

Verwendung:
    uv run dbreset
"""

import logging

from app.core import get_app_root, init_db, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Löscht die Datenbankdatei und legt das Schema neu an."""
    setup_logging()
    db_path = get_app_root() / "data" / "schnappster.db"

    if db_path.exists():
        db_path.unlink()
        logger.info(f"Deleted {db_path}")

    init_db()
    logger.info("Database recreated")
