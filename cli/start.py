"""Start the Schnappster application.

Usage:
    uv run start                      # run tests, build web, start app (port 8000)
    uv run start --port 8080          # use port 8080
    uv run start --skip-tests         # skip tests, build web, start app
    uv run start --dev                # dev mode: Next.js :3000 + backend
    uv run start --dev --port 8080    # dev mode on port 8080
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

DEFAULT_PORT = 8000


def _parse_start_args() -> tuple[int, bool, bool]:
    """Parse sys.argv for start command. Returns (port, skip_tests, dev_mode)."""
    argv = sys.argv[1:]
    port = DEFAULT_PORT
    skip_tests = False
    dev_mode = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--port":
            if i + 1 < len(argv):
                try:
                    port = int(argv[i + 1])
                except ValueError:
                    print("Error: --port requires a number", file=sys.stderr)
                    sys.exit(1)
                if not (1 <= port <= 65535):
                    print("Error: port must be between 1 and 65535", file=sys.stderr)
                    sys.exit(1)
                i += 2
                continue
            else:
                print("Error: --port requires a value", file=sys.stderr)
                sys.exit(1)
        if arg.startswith("--port="):
            try:
                port = int(arg.split("=", 1)[1])
            except ValueError:
                print("Error: --port= requires a number", file=sys.stderr)
                sys.exit(1)
            if not (1 <= port <= 65535):
                print("Error: port must be between 1 and 65535", file=sys.stderr)
                sys.exit(1)
            i += 1
            continue
        if arg == "--skip-tests":
            skip_tests = True
        elif arg == "--dev":
            dev_mode = True
        i += 1
    return port, skip_tests, dev_mode


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


def start_frontend_dev(port: int) -> subprocess.Popen[bytes]:
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
        env={**os.environ, "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{port}"},
    )
    return proc


def main() -> None:
    setup_logging()

    port, skip_tests, dev_mode = _parse_start_args()

    if not skip_tests and not run_tests():
        print("\n❌  Tests failed. Fix them or use --skip-tests to skip.\n")
        sys.exit(1)

    if dev_mode:
        print("\n" + "=" * 60)
        print("🔧  SCHNAPPSTER DEV MODE")
        print("=" * 60)
        print("  Frontend: http://localhost:3000")
        print(f"  Backend:  http://localhost:{port}")
        print("=" * 60 + "\n")
        frontend_proc: subprocess.Popen[bytes] | None = None
        try:
            frontend_proc = start_frontend_dev(port)
            uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True, log_config=None)
        finally:
            if frontend_proc and frontend_proc.poll() is None:
                frontend_proc.terminate()
    else:
        build_frontend()
        print("\n" + "=" * 60)
        print("🚀  STARTING SCHNAPPSTER")
        print("=" * 60)
        print(f"  App:      http://localhost:{port}")
        print("=" * 60 + "\n")
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True, log_config=None)
