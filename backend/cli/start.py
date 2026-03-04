"""Start the Schnappster application.

Usage:
    uv run start              # start with tests
    uv run start --skip-tests # start without tests
"""

import logging
import subprocess
import sys

import uvicorn

from app.core import setup_logging

logger = logging.getLogger(__name__)


def run_tests() -> bool:
    """Run pytest and return True if all tests pass."""
    logger.info("Running tests...")
    result = subprocess.run(["uv", "run", "pytest", "tests/", "-v"])
    return result.returncode == 0


def main() -> None:
    setup_logging()

    skip_tests = "--skip-tests" in sys.argv

    if not skip_tests:
        if not run_tests():
            logger.error("Tests failed. Fix them or use --skip-tests to skip.")
            sys.exit(1)
        logger.info("All tests passed!")

    logger.info("Starting Schnappster...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
