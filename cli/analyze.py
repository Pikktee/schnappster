"""Manual AI analysis invocation.

Usage:
    uv run analyze           # analyze up to 10 unprocessed ads
    uv run analyze 50        # analyze up to 50 unprocessed ads
"""

import logging
import sys

from sqlmodel import Session

from app.core import db_engine, setup_logging
from app.services.ai import AIService

logger = logging.getLogger(__name__)


def main() -> None:
    """Run AI analysis for unprocessed ads; limit from argv or default 10."""
    setup_logging()

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    with Session(db_engine) as session:
        try:
            ai_service = AIService(session)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)

        analyzed = ai_service.analyze_unprocessed(limit=limit)
        logger.info(f"Analyzed {analyzed} ads")
