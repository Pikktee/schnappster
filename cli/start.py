"""Start the Schnappster application.

Usage:
    uv run start                 # run tests, build web, start app with static frontend
    uv run start --skip-tests    # skip tests, build web, start app with static frontend
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
    # Print a visually distinct header that stands out
    print("\n" + "=" * 60)
    print("🧪  RUNNING TESTS")
    print("=" * 60 + "\n")

    result = subprocess.run(["uv", "run", "pytest", "tests/", "-v"], check=False)

    # Print a clear pass/fail footer
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅  ALL TESTS PASSED")
    else:
        print("❌  TESTS FAILED")
    print("=" * 60 + "\n")

    return result.returncode == 0


def get_project_root() -> Path:
    """Project root (same as app root)."""
    return get_app_root()


def get_frontend_dir() -> Path:
    return get_app_root() / "web"


def build_frontend() -> None:
    """Build the Next.js frontend as static export into web/out."""
    frontend_dir = get_frontend_dir()
    if not frontend_dir.exists():
        logger.warning(
            "Frontend directory %s does not exist. Skipping frontend build.", frontend_dir
        )
        return

    print("\n" + "=" * 60)
    print("📦  BUILDING FRONTEND")
    print("=" * 60 + "\n")

    print("Installing frontend dependencies (npm install)...\n")
    result_install = subprocess.run(
        ["npm", "install"],
        cwd=str(frontend_dir),
        check=False,
    )
    if result_install.returncode != 0:
        print("\n" + "=" * 60)
        print("❌  NPM INSTALL FAILED")
        print("=" * 60 + "\n")
        sys.exit(result_install.returncode)

    print("\nBuilding frontend (npm run export)...\n")
    result_export = subprocess.run(
        ["npm", "run", "export"],
        cwd=str(frontend_dir),
        check=False,
    )
    if result_export.returncode != 0:
        print("\n" + "=" * 60)
        print("❌  FRONTEND BUILD FAILED")
        print("=" * 60 + "\n")
        sys.exit(result_export.returncode)

    print("\n" + "=" * 60)
    print("✅  FRONTEND BUILD COMPLETED")
    print("=" * 60 + "\n")


def start_frontend_dev() -> subprocess.Popen[bytes]:
    """Start the Next.js dev server (npm run dev) and return the process."""
    frontend_dir = get_frontend_dir()
    if not frontend_dir.exists():
        logger.error("Frontend directory %s does not exist. Cannot start dev server.", frontend_dir)
        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("🚀  STARTING FRONTEND DEV SERVER")
    print("=" * 60 + "\n")

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
            print("\n❌  Tests failed. Fix them or use --skip-tests to skip.\n")
            sys.exit(1)

    if dev_mode:
        print("\n" + "=" * 60)
        print("🔧  SCHNAPPSTER DEV MODE")
        print("=" * 60)
        print("  Frontend: http://localhost:3000")
        print("  Backend:  http://localhost:8000")
        print("=" * 60 + "\n")
        frontend_proc: subprocess.Popen[bytes] | None = None
        try:
            frontend_proc = start_frontend_dev()
            uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, log_config=None)
        finally:
            if frontend_proc and frontend_proc.poll() is None:
                frontend_proc.terminate()
    else:
        build_frontend()
        print("\n" + "=" * 60)
        print("🚀  STARTING SCHNAPPSTER")
        print("=" * 60)
        print("  App:      http://localhost:8000")
        print("=" * 60 + "\n")
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, log_config=None)
