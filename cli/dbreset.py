"""Reset database and optionally create example data.

Usage:
    uv run dbreset              # Drop DB, recreate schema only
    uv run dbreset --seed       # Also create example AdSearch
"""

import argparse
import logging

from sqlmodel import Session

from app.core import db_engine, get_app_root, init_db, setup_logging
from app.models import AdSearch

logger = logging.getLogger(__name__)


def main() -> None:
    """Drop database file, recreate schema; optionally create example AdSearch."""
    parser = argparse.ArgumentParser(
        description="Datenbank löschen und neu anlegen (optional mit Beispiel-Suchauftrag)."
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Beispiel-AdSearch (PodMic Frankfurt) anlegen",
    )
    args = parser.parse_args()

    setup_logging()
    db_path = get_app_root() / "data" / "schnappster.db"

    if db_path.exists():
        db_path.unlink()
        logger.info(f"Deleted {db_path}")

    init_db()
    logger.info("Database recreated")

    if args.seed:
        with Session(db_engine) as session:
            session.add(
                AdSearch(
                    name="PodMic Frankfurt",
                    url="https://www.kleinanzeigen.de/s-audio-hifi/60325/podmic/k0c172l4305r250",
                )
            )
            session.commit()
            logger.info("Example AdSearch created")
