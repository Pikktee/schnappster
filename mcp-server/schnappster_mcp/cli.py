"""Repo-Root-CLI für das MCP-Unterprojekt: Server starten, optional Quick Tunnel.

Aus dem Schnappster-Repository-Root (nach ``uv sync``):

    uv run mcp-server                  # delegiert zu ``schnappster-mcp``
    uv run mcp-server --tunnel         # TryCloudflare + MCP (MCP_RESOURCE_SERVER_URL gesetzt)
    uv run mcp-server -- …             # Argumente an ``schnappster-mcp`` durchreichen

Nur Tunnel ohne MCP: ``cloudflared tunnel --url http://127.0.0.1:8766``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

QUICK_TUNNEL_URL_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)

TUNNEL_URL_TIMEOUT_S = 90
_CHILD_TERMINATE_TIMEOUT_S = 5.0


def extract_trycloudflare_public_base(line: str) -> str | None:
    m = QUICK_TUNNEL_URL_RE.search(line)
    if not m:
        return None
    return m.group(0).rstrip("/")


def ensure_cloudflared() -> str:
    path = shutil.which("cloudflared")
    if path:
        return path
    if sys.platform == "darwin":
        print(
            "cloudflared nicht gefunden — versuche Installation mit Homebrew …",
            file=sys.stderr,
        )
        result = subprocess.run(["brew", "install", "cloudflared"], check=False)
        if result.returncode != 0:
            print(
                "Homebrew-Installation fehlgeschlagen. Manuell: brew install cloudflared\n"
                "Oder: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
                file=sys.stderr,
            )
            sys.exit(1)
        path = shutil.which("cloudflared")
        if not path:
            print(
                "cloudflared nach brew install nicht im PATH — neues Terminal oder PATH prüfen.",
                file=sys.stderr,
            )
            sys.exit(1)
        return path

    print(
        "cloudflared nicht installiert.\n"
        "Anleitung: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
        file=sys.stderr,
    )
    sys.exit(1)


def _mcp_project_dir() -> Path:
    """Absolute path to ``mcp-server/`` (parent of package ``schnappster_mcp``)."""
    return Path(__file__).resolve().parent.parent


def _resolve_mcp_dir() -> Path:
    mcp_dir = _mcp_project_dir()
    if not (mcp_dir / "pyproject.toml").is_file():
        print(
            "mcp-server/pyproject.toml nicht gefunden — "
            "cli.py muss im Paket schnappster_mcp liegen.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return mcp_dir


def _schnappster_mcp_command(mcp_dir: Path, mcp_argv: list[str]) -> list[str]:
    exe = shutil.which("schnappster-mcp")
    if exe:
        return [exe, *mcp_argv]
    return ["uv", "run", "--project", str(mcp_dir), "schnappster-mcp", *mcp_argv]


def _mcp_path_from_env() -> str:
    path = os.environ.get("STREAMABLE_HTTP_PATH", "/mcp").strip() or "/mcp"
    return path if path.startswith("/") else f"/{path}"


def _terminate(
    proc: subprocess.Popen[str] | None,
    timeout: float = _CHILD_TERMINATE_TIMEOUT_S,
) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


class _ChildProcs:
    cf: subprocess.Popen[str] | None = None
    mcp: subprocess.Popen[str] | None = None


def run_with_quick_tunnel(port: int, mcp_argv: list[str]) -> None:
    mcp_dir = _resolve_mcp_dir()
    cf_exe = ensure_cloudflared()
    local_url = f"http://127.0.0.1:{port}"
    url_ready = threading.Event()
    public_base_holder: list[str] = []
    procs = _ChildProcs()

    def cleanup() -> None:
        _terminate(procs.mcp)
        _terminate(procs.cf)

    def on_signal(_signum: int, _frame: object | None) -> None:
        cleanup()
        sys.exit(128 + _signum)

    def read_cf_stderr() -> None:
        assert procs.cf is not None and procs.cf.stderr is not None
        try:
            for line in procs.cf.stderr:
                sys.stderr.write(line)
                sys.stderr.flush()
                if url_ready.is_set():
                    continue
                base = extract_trycloudflare_public_base(line)
                if base:
                    public_base_holder.append(base)
                    url_ready.set()
        except (BrokenPipeError, ValueError):
            pass

    procs.cf = subprocess.Popen(
        [cf_exe, "tunnel", "--url", local_url],
        stdout=None,
        stderr=subprocess.PIPE,
        text=True,
    )
    threading.Thread(target=read_cf_stderr, daemon=True).start()

    deadline = time.monotonic() + TUNNEL_URL_TIMEOUT_S
    while time.monotonic() < deadline:
        if url_ready.wait(timeout=0.2):
            break
        if procs.cf.poll() is not None:
            print(
                "cloudflared ist beendet, bevor eine TryCloudflare-URL erkannt wurde.",
                file=sys.stderr,
            )
            cleanup()
            raise SystemExit(1)

    if not url_ready.is_set():
        print(
            f"Keine TryCloudflare-URL innerhalb von {TUNNEL_URL_TIMEOUT_S}s "
            "in der cloudflared-Ausgabe.",
            file=sys.stderr,
        )
        cleanup()
        raise SystemExit(1)

    public_base = public_base_holder[0]
    resource_url = f"{public_base}{_mcp_path_from_env()}"
    child_env = os.environ | {"MCP_RESOURCE_SERVER_URL": resource_url}

    print(
        f"MCP_RESOURCE_SERVER_URL gesetzt (nur für diesen MCP-Prozess): {resource_url}\n"
        "Kein Eintrag in .env nötig. Strg+C beendet Tunnel und MCP.",
        file=sys.stderr,
    )

    old_int = signal.signal(signal.SIGINT, on_signal)
    old_term: object | None = None
    if hasattr(signal, "SIGTERM"):
        old_term = signal.signal(signal.SIGTERM, on_signal)

    code = 1
    try:
        mcp_proc = subprocess.Popen(
            _schnappster_mcp_command(mcp_dir, mcp_argv),
            env=child_env,
            text=True,
        )
        procs.mcp = mcp_proc
        code = mcp_proc.wait()
    except KeyboardInterrupt:
        code = 130
    finally:
        signal.signal(signal.SIGINT, old_int)
        if old_term is not None and hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, old_term)
        cleanup()

    raise SystemExit(code)


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] == "tunnel":
        print(
            "Der Unterbefehl „mcp tunnel“ gibt es nicht mehr.\n"
            "  uv run mcp-server --tunnel\n"
            "    Quick Tunnel und MCP zusammen; MCP_RESOURCE_SERVER_URL wird gesetzt.\n"
            "  cloudflared tunnel --url http://127.0.0.1:8766\n"
            "    Nur Tunnel; MCP separat mit „uv run mcp-server“ "
            "und MCP_RESOURCE_SERVER_URL in .env.",
            file=sys.stderr,
        )
        sys.exit(2)

    parser = argparse.ArgumentParser(
        prog="mcp-server",
        description=(
            "Schnappster Remote-MCP: ohne --tunnel wird schnappster-mcp gestartet; "
            "mit --tunnel Quick Tunnel (TryCloudflare) plus MCP mit MCP_RESOURCE_SERVER_URL."
        ),
    )
    parser.add_argument("--tunnel", "-t", action="store_true")
    parser.add_argument("--port", "-p", type=int, default=8766, metavar="PORT")
    ns, rest = parser.parse_known_args(argv)

    if ns.tunnel:
        run_with_quick_tunnel(port=ns.port, mcp_argv=rest)
        return

    mcp_dir = _resolve_mcp_dir()
    cmd = _schnappster_mcp_command(mcp_dir, rest)
    raise SystemExit(subprocess.call(cmd))
