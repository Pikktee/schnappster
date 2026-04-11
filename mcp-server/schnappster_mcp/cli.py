"""Repo-Root-CLI für das MCP-Unterprojekt: Server starten, optional Quick Tunnel.

Aus dem Schnappster-Repository-Root (nach ``uv sync``):

    uv run mcp-server                    # delegiert zu ``schnappster-mcp``
    uv run mcp-server --tunnel           # Quick Tunnel + MCP (ein lokaler Port)
    uv run mcp-server --tunnel --mitmdump   # zusätzlich mitmdump; Klartext → logs/
    uv run mcp-server -- …               # Argumente an ``schnappster-mcp`` durchreichen

Nur Tunnel ohne MCP: ``cloudflared tunnel --url http://127.0.0.1:8766``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TextIO

QUICK_TUNNEL_URL_RE = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com",
    re.IGNORECASE,
)

TUNNEL_URL_TIMEOUT_S = 90
_CHILD_TERMINATE_TIMEOUT_S = 5.0
_MAX_TUNNEL_STARTUP_LOG_LINES = 120
_MITM_LISTEN_WAIT_S = 10.0
_MCP_BIND_WAIT_S = 30.0
_MAX_FRONT_PORT = 65534


def quick_tunnel_backend_port(front_port: int) -> int:
    """Lokaler MCP-Bind-Port, wenn mitmproxy vor cloudflared auf ``front_port`` lauscht."""
    return front_port + 1


def quick_tunnel_with_mitmdump(*, with_mitmdump: bool, mitmdump_executable: str | None) -> bool:
    """True, wenn ``--mitmdump`` gesetzt und ``mitmdump`` im PATH ist."""
    return with_mitmdump and mitmdump_executable is not None


def _mitmdump_logs_dir(mcp_dir: Path) -> Path:
    """Repo-``logs/`` (Schwester von ``mcp-server/``)."""
    return mcp_dir.parent / "logs"


def _open_new_mitmdump_trace_log(mcp_dir: Path) -> tuple[Path, TextIO]:
    log_dir = _mitmdump_logs_dir(mcp_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    path = log_dir / f"mcp_mitmdump_{stamp}.log"
    fp = path.open("w", encoding="utf-8", buffering=1)
    fp.write(f"# Schnappster mcp-server mitmdump ({time.strftime('%Y-%m-%d %H:%M:%S')})\n\n")
    fp.flush()
    return path, fp


def extract_trycloudflare_public_base(line: str) -> str | None:
    m = QUICK_TUNNEL_URL_RE.search(line)
    if not m:
        return None
    return m.group(0).rstrip("/")


def _cloudflared_line_is_likely_error(line: str) -> bool:
    """Nur auffällige Log-Level durchreichen (nachdem die Tunnel-URL schon da ist)."""
    return bool(re.search(r"\b(ERR|FTL|CRIT|PANIC)\b", line))


def _print_tunnel_ready_banner(resource_url: str) -> None:
    """Kompakte, gut lesbare Ausgabe des öffentlichen MCP-Endpunkts (stdout)."""
    body = [
        "Öffentlicher MCP-Endpunkt",
        "",
        "Diese URL im MCP-Client eintragen; Authentifizierung mit Supabase Access Token (Bearer).",
        "",
        resource_url,
    ]
    inner_w = max(len(line) for line in body)
    rule = "─" * (inner_w + 2)
    lines = [f"│ {line:<{inner_w}} │" for line in body]
    print()
    print(f"╭{rule}╮", flush=True)
    for row in lines:
        print(row, flush=True)
    print(f"╰{rule}╯", flush=True)
    print(flush=True)


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


def _wait_tcp_accept(host: str, port: int, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _env_for_mcp_tunnel_warmup(backend_port: int) -> dict[str, str]:
    """Warmup-MCP vor mitm: ohne MCP_RESOURCE_SERVER_URL (Default localhost)."""
    env = dict(os.environ)
    env.pop("MCP_RESOURCE_SERVER_URL", None)
    env["MCP_PORT"] = str(backend_port)
    return env


def _mitmdump_addon_script() -> Path:
    return Path(__file__).resolve().parent / "mitm_tunnel_trace_addon.py"


def _mitmdump_reverse_command(
    mitmdump_exe: str,
    *,
    front_port: int,
    backend_port: int,
) -> list[str]:
    # Siehe mitmproxy mode_specs: reverse:UPSTREAM@listen_host:listen_port
    up = f"http://127.0.0.1:{backend_port}"
    mode = f"reverse:{up}@127.0.0.1:{front_port}"
    addon = _mitmdump_addon_script()
    # flow_detail=0: Standard-Dumper nur minimal; Klartext kommt aus mitm_tunnel_trace_addon.py
    return [
        mitmdump_exe,
        "--mode",
        mode,
        "--set",
        "flow_detail=0",
        "-s",
        str(addon),
    ]


class _ChildProcs:
    cf: subprocess.Popen[str] | None = None
    mitm: subprocess.Popen[str] | None = None
    mitm_log_file: TextIO | None = None
    mcp: subprocess.Popen[str] | None = None


def run_with_quick_tunnel(
    port: int,
    mcp_argv: list[str],
    *,
    with_mitmdump: bool = False,
) -> None:
    mcp_dir = _resolve_mcp_dir()
    cf_exe = ensure_cloudflared()
    mitmdump_exe = shutil.which("mitmdump")
    use_mitm = quick_tunnel_with_mitmdump(
        with_mitmdump=with_mitmdump,
        mitmdump_executable=mitmdump_exe,
    )
    if with_mitmdump and mitmdump_exe is None:
        print(
            "mitmdump nicht im PATH — für --mitmdump installieren: "
            "brew install mitmproxy (oder pipx install mitmproxy).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if use_mitm and port > _MAX_FRONT_PORT:
        need = port + 1
        msg = f"--port muss ≤ {_MAX_FRONT_PORT} sein (mit --mitmdump: MCP auf {need})."
        print(msg, file=sys.stderr)
        raise SystemExit(1)

    backend_port = quick_tunnel_backend_port(port) if use_mitm else port
    local_url = f"http://127.0.0.1:{port}"

    url_ready = threading.Event()
    public_base_holder: list[str] = []
    startup_log: list[str] = []
    startup_log_lock = threading.Lock()
    procs = _ChildProcs()

    def cleanup() -> None:
        _terminate(procs.mcp)
        _terminate(procs.mitm)
        if procs.mitm_log_file is not None:
            try:
                procs.mitm_log_file.flush()
                procs.mitm_log_file.close()
            except OSError:
                pass
            procs.mitm_log_file = None
        _terminate(procs.cf)

    def on_signal(_signum: int, _frame: object | None) -> None:
        cleanup()
        sys.exit(128 + _signum)

    if use_mitm:
        assert mitmdump_exe is not None
        procs.mcp = subprocess.Popen(
            _schnappster_mcp_command(mcp_dir, mcp_argv),
            env=_env_for_mcp_tunnel_warmup(backend_port),
            text=True,
        )
        if not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
            w = int(_MCP_BIND_WAIT_S)
            msg = f"MCP (Warmup) lauscht nach {w}s nicht auf 127.0.0.1:{backend_port}."
            print(msg, file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        mitm_log_path, mitm_fp = _open_new_mitmdump_trace_log(mcp_dir)
        procs.mitm_log_file = mitm_fp
        print(
            f"mitmdump: Klartext-Log → {mitm_log_path.resolve()}",
            file=sys.stderr,
            flush=True,
        )
        mitm_env = os.environ | {"SCHNAPPSTER_MITM_MCP_PATH": _mcp_path_from_env()}
        procs.mitm = subprocess.Popen(
            _mitmdump_reverse_command(mitmdump_exe, front_port=port, backend_port=backend_port),
            stdin=subprocess.DEVNULL,
            stdout=mitm_fp,
            stderr=subprocess.STDOUT,
            text=True,
            env=mitm_env,
        )
        time.sleep(0.15)
        if procs.mitm.poll() is not None:
            print("mitmdump sofort beendet — Trace-Modus nicht nutzbar.", file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        if not _wait_tcp_accept("127.0.0.1", port, _MITM_LISTEN_WAIT_S):
            print(
                f"mitmdump lauscht nach {_MITM_LISTEN_WAIT_S:.0f}s nicht auf 127.0.0.1:{port}.",
                file=sys.stderr,
            )
            cleanup()
            raise SystemExit(1)

    def read_cf_stderr() -> None:
        assert procs.cf is not None and procs.cf.stderr is not None
        try:
            for line in procs.cf.stderr:
                if url_ready.is_set():
                    if _cloudflared_line_is_likely_error(line):
                        sys.stderr.write(line)
                        sys.stderr.flush()
                    continue
                with startup_log_lock:
                    if len(startup_log) < _MAX_TUNNEL_STARTUP_LOG_LINES:
                        startup_log.append(line)
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
                "cloudflared ist beendet, bevor eine Quick-Tunnel-URL (*.trycloudflare.com) "
                "erkannt wurde.",
                file=sys.stderr,
            )
            with startup_log_lock:
                tail = "".join(startup_log)
            if tail.strip():
                print("Ausgabe von cloudflared:", file=sys.stderr)
                sys.stderr.write(tail)
                if not tail.endswith("\n"):
                    sys.stderr.write("\n")
                sys.stderr.flush()
            cleanup()
            raise SystemExit(1)
        if use_mitm and procs.mitm is not None and procs.mitm.poll() is not None:
            print("mitmdump ist während des Tunnel-Starts beendet worden.", file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        if use_mitm and procs.mcp is not None and procs.mcp.poll() is not None:
            print("MCP (Warmup) ist während des Tunnel-Starts beendet worden.", file=sys.stderr)
            cleanup()
            raise SystemExit(1)

    if not url_ready.is_set():
        print(
            f"Keine Quick-Tunnel-URL (*.trycloudflare.com) innerhalb von {TUNNEL_URL_TIMEOUT_S}s "
            "in der cloudflared-Ausgabe.",
            file=sys.stderr,
        )
        with startup_log_lock:
            tail = "".join(startup_log)
        if tail.strip():
            print("Ausgabe von cloudflared:", file=sys.stderr)
            sys.stderr.write(tail)
            if not tail.endswith("\n"):
                sys.stderr.write("\n")
            sys.stderr.flush()
        cleanup()
        raise SystemExit(1)

    public_base = public_base_holder[0]
    resource_url = f"{public_base}{_mcp_path_from_env()}"
    child_env = os.environ | {"MCP_RESOURCE_SERVER_URL": resource_url}
    if use_mitm:
        child_env = child_env | {"MCP_PORT": str(backend_port)}
        _terminate(procs.mcp)

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
        if use_mitm and not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
            print(
                f"MCP lauscht nach Setzen der Tunnel-URL nicht auf 127.0.0.1:{backend_port}.",
                file=sys.stderr,
            )
            cleanup()
            raise SystemExit(1)
        _print_tunnel_ready_banner(resource_url)
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
            "    Quick Tunnel und MCP zusammen; öffentliche URL erscheint oben.\n"
            "  cloudflared tunnel --url http://127.0.0.1:8766\n"
            "    Nur Tunnel; MCP separat mit „uv run mcp-server“ "
            "(öffentliche URL ggf. in .env, siehe .env.example).",
            file=sys.stderr,
        )
        sys.exit(2)

    parser = argparse.ArgumentParser(
        prog="mcp-server",
        description=(
            "Schnappster Remote-MCP: ohne --tunnel wird schnappster-mcp gestartet; "
            "mit --tunnel zusätzlich Cloudflare Quick Tunnel und ausgegebener öffentlicher URL."
        ),
    )
    parser.add_argument("--tunnel", "-t", action="store_true")
    parser.add_argument(
        "--mitmdump",
        action="store_true",
        help=(
            "Nur mit --tunnel: mitmdump-Reverse vor cloudflared; MCP-Klartext in logs/ "
            "(Dateipfad auf stderr)."
        ),
    )
    parser.add_argument("--port", "-p", type=int, default=8766, metavar="PORT")
    ns, rest = parser.parse_known_args(argv)

    if ns.mitmdump and not ns.tunnel:
        parser.error("--mitmdump setzt --tunnel voraus.")

    if ns.tunnel:
        run_with_quick_tunnel(
            port=ns.port,
            mcp_argv=rest,
            with_mitmdump=ns.mitmdump,
        )
        return

    mcp_dir = _resolve_mcp_dir()
    cmd = _schnappster_mcp_command(mcp_dir, rest)
    raise SystemExit(subprocess.call(cmd))
