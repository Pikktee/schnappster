"""Start the Schnappster application.

Usage:
    uv run start                 # run tests, build frontend, start backend with static frontend
    uv run start --skip-tests    # skip tests, build frontend, start backend with static frontend
    uv run start --dev           # dev mode: tests, then start Next dev server + backend
    uv run start --dev --skip-tests
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from app.core import get_app_root, setup_logging

logger = logging.getLogger(__name__)


def run_tests() -> bool:
    """Run pytest and return True if all tests pass."""
    logger.info("Running tests...")
    result = subprocess.run(["uv", "run", "pytest", "tests/", "-v"], check=False)
    return result.returncode == 0


def get_project_root() -> Path:
    """Project root is the parent of the backend/app root (where frontend/ lives)."""
    return get_app_root().parent


def get_frontend_dir() -> Path:
    return get_project_root() / "frontend"


def build_frontend() -> None:
    """Build the Next.js frontend as static export into frontend/out."""
    frontend_dir = get_frontend_dir()
    if not frontend_dir.exists():
        logger.warning("Frontend directory %s does not exist. Skipping frontend build.", frontend_dir)
        return

    logger.info("Installing frontend dependencies (npm install)...")
    result_install = subprocess.run(
        ["npm", "install"],
        cwd=str(frontend_dir),
        check=False,
    )
    if result_install.returncode != 0:
        logger.error("npm install failed with exit code %s", result_install.returncode)
        sys.exit(result_install.returncode)

    logger.info("Building frontend (npm run export)...")
    result_export = subprocess.run(
        ["npm", "run", "export"],
        cwd=str(frontend_dir),
        check=False,
    )
    if result_export.returncode != 0:
        logger.error("npm run export failed with exit code %s", result_export.returncode)
        sys.exit(result_export.returncode)

    logger.info("Frontend build completed successfully.")


def start_frontend_dev() -> subprocess.Popen[bytes]:
    """Start the Next.js dev server (npm run dev) and return the process."""
    frontend_dir = get_frontend_dir()
    if not frontend_dir.exists():
        logger.error("Frontend directory %s does not exist. Cannot start dev server.", frontend_dir)
        raise SystemExit(1)

    logger.info("Starting frontend dev server (npm run dev)...")
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        env={**os.environ, "NEXT_PUBLIC_API_URL": "http://127.0.0.1:8000"},
    )
    return proc


def main() -> None:
    setup_logging()

    args = set(sys.argv[1:])
    skip_tests = "--skip-tests" in args
    dev_mode = "--dev" in args

    if not skip_tests:
        if not run_tests():
            logger.error("Tests failed. Fix them or use --skip-tests to skip.")
            sys.exit(1)
        logger.info("All tests passed!")

    if dev_mode:
        logger.info("Starting Schnappster in DEV mode (Next dev server + backend)...")
        frontend_proc: subprocess.Popen[bytes] | None = None
        try:
            frontend_proc = start_frontend_dev()
            uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
        finally:
            if frontend_proc and frontend_proc.poll() is None:
                logger.info("Stopping frontend dev server...")
                frontend_proc.terminate()
    else:
        logger.info("Building frontend for static export...")
        build_frontend()
        logger.info("Starting Schnappster with static frontend...")
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
