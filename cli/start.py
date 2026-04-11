"""Startet die Schnappster-API.

Verwendung:
    uv run start                      # Tests und API starten (Port 8000)
    uv run start --port 8080          # Port 8080 nutzen
    uv run start --skip-tests         # Tests überspringen, API starten
    uv run start --dev                # Dev-Modus: Next.js :3000 + Backend
    uv run start --dev --port 8080    # Dev-Modus auf Port 8080
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from app.core import config, get_app_root, setup_logging

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000


def _parse_start_args() -> tuple[int, bool, bool]:
    """Parst sys.argv für den start-Befehl; gibt (port, skip_tests, dev_mode) zurück."""
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
    """Führt pytest aus und gibt True zurück, wenn alle Tests bestehen."""
    # Deutlich sichtbare Kopfzeile ausgeben
    print("\n" + "=" * 60)
    print("🧪  RUNNING TESTS")
    print("=" * 60 + "\n")

    result = subprocess.run(["uv", "run", "pytest", "tests/", "-v"], check=False)

    # Klare Bestanden/Fehlgeschlagen-Fußzeile
    print("\n" + "=" * 60)
    if result.returncode == 0:
        print("✅  ALL TESTS PASSED")
    else:
        print("❌  TESTS FAILED")
    print("=" * 60 + "\n")

    return result.returncode == 0


def get_frontend_dir() -> Path:
    """Gibt den Pfad zum Web-Frontend-Verzeichnis (Next.js) zurück."""
    return get_app_root() / "web"


def start_frontend_dev(port: int) -> subprocess.Popen[bytes]:
    """Startet den Next.js-Dev-Server (npm run dev) und gibt den Prozess zurück."""
    frontend_dir = get_frontend_dir()
    if not frontend_dir.exists():
        logger.error("Frontend directory %s does not exist. Cannot start dev server.", frontend_dir)
        raise SystemExit(1)

    print("\n" + "=" * 60)
    print("🚀  STARTING FRONTEND DEV SERVER")
    print("=" * 60 + "\n")

    frontend_env = {
        **os.environ,
        "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{port}",
    }
    if config.supabase_url.strip():
        frontend_env["NEXT_PUBLIC_SUPABASE_URL"] = config.supabase_url
    if config.supabase_publishable_key.strip():
        frontend_env["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"] = config.supabase_publishable_key

    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        env=frontend_env,
    )
    return proc


def main() -> None:
    """Argumente parsen, Tests (optional), Dev-Frontend bei --dev, Uvicorn starten."""
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
        print("\n" + "=" * 60)
        print("🚀  STARTING SCHNAPPSTER API")
        print("=" * 60)
        print(f"  App:      http://localhost:{port}")
        print("=" * 60 + "\n")
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True, log_config=None)
