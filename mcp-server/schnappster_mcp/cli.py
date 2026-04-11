"""Repo-Root-CLI für das MCP-Unterprojekt: interaktiver Supervisor, optional Quick Tunnel.

Aus dem Schnappster-Repository-Root (nach ``uv sync``):

    uv run mcp-server                 # TTY: Quick-Tunnel; Steuerung in der Start-Box
    uv run mcp-server --http-proxy    # TTY: mitmdump von Anfang an; p schaltet Proxy um
    uv run mcp-server --tunnel        # Nur ohne TTY: einmaliger Start mit TryCloudflare
    uv run mcp-server -- …            # Argumente an ``schnappster-mcp`` durchreichen

Ohne TTY (CI/Skripte): einmaliger Start ohne Supervisor (lokal bzw. ein gebündelter Tunnel-Lauf).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import re
import select
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
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
    """True, wenn HTTP-Proxy (mitmdump) aktiv sein soll und ``mitmdump`` im PATH ist."""
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


def _discard_cloudflared_diagnostic(_message: str) -> None:
    """cloudflared-Zeilen nach URL im TTY-Supervisor nicht auf stderr ausgeben."""


# Kompakte Box (~72 Spalten Text); Schnappster: Orange/Stein (256-Farben, respektiert NO_COLOR).
_MCP_BOX_TEXT_W = 72
_RST = "\033[0m"
_SN_BOX = "\033[38;5;208m"
_SN_TITLE = "\033[1;38;5;208m"
_SN_BODY = "\033[38;5;245m"
_SN_URL = "\033[38;5;214;4m"
_SN_KEY = "\033[38;5;223m"
_SN_KEY_CHAR = "\033[1;38;5;231m"  # r / p / q etwas heller


def _wrap_resource_url_lines(url: str, width: int) -> list[str]:
    """URL umbrechen, bevorzugt an ``/`` (vermeidet Zerhacken mitten in ``.com``/Host)."""
    u = url.strip()
    if len(u) <= width:
        return [u]
    lines: list[str] = []
    rest = u
    while rest:
        if len(rest) <= width:
            lines.append(rest)
            break
        cut = rest.rfind("/", 1, width + 1)
        if cut <= 0:
            lines.append(rest[:width])
            rest = rest[width:]
            continue
        lines.append(rest[: cut + 1])
        rest = rest[cut + 1 :]
    return lines


def _style_key_help_line(text: str, *, rs: str) -> str:
    """Hebt alle ``r``/``p``/``q`` vor je zwei Leerzeichen hervor (eine Tastenzeile)."""
    k = _SN_KEY
    bright = _SN_KEY_CHAR
    out: list[str] = []
    last = 0
    for m in re.finditer(r"([rpq])(  )", text):
        out.append(f"{k}{text[last : m.start()]}{rs}")
        out.append(f"{bright}{m.group(1)}{rs}{k}{m.group(2)}{rs}")
        last = m.end()
    out.append(f"{k}{text[last:]}{rs}")
    return "".join(out)


def _print_mcp_url_box(resource_url: str, *, show_keypad: bool = False) -> None:
    """Eine Box: Titel, URL (umgebrochen), optional Tasten."""
    w = _MCP_BOX_TEXT_W
    rows: list[tuple[str, str]] = [
        ("title", "Schnappster MCP-Server"),
        ("gap", ""),
    ]
    for part in _wrap_resource_url_lines(resource_url.strip(), w):
        rows.append(("url", part))
    if show_keypad:
        rows.append(("gap", ""))
        rows.append(("body", "Tasten:"))
        rows.append(("key", "r  MCP-Neustart   p  HTTP-Proxy starten   q  Ende"))

    inner_w = max((len(t) for k, t in rows if k != "gap" or t), default=1)

    use_color = _ansi_stdout()
    b = _SN_BOX if use_color else ""
    rs = _RST if use_color else ""

    def styled(kind: str, text: str) -> str:
        if not use_color or not text:
            return text
        if kind == "title":
            return f"{_SN_TITLE}{text}{rs}"
        if kind == "body":
            return f"{_SN_BODY}{text}{rs}"
        if kind == "url":
            return f"{_SN_URL}{text}{rs}"
        if kind == "key":
            return _style_key_help_line(text, rs=rs)
        return text

    rule = "─" * (inner_w + 2)
    print()
    print(f"{b}╭{rule}╮{rs}", flush=True)
    for kind, text in rows:
        if kind == "gap" and not text:
            mid = " " * inner_w
        else:
            cell = styled(kind, text)
            pad = inner_w - len(text)
            mid = cell + (" " * pad if pad > 0 else "")
        print(f"{b}│{rs} {mid} {b}│{rs}", flush=True)
    print(f"{b}╰{rule}╯{rs}", flush=True)
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


def _effective_streamable_http_path() -> str:
    """Gleicher MCP-Pfad wie im Server (Settings inkl. .env), nicht nur ``os.environ``.

    Der Tunnel setzt ``MCP_RESOURCE_SERVER_URL`` im Parent-Prozess; ``os.environ`` enthält
    ``STREAMABLE_HTTP_PATH`` oft nicht, obwohl er in der Repo-``.env`` steht — dann wäre
    die öffentliche URL (Pfad-Suffix) falsch und OAuth/Clients würden am falschen Pfad
    landen.
    """
    from schnappster_mcp.config import Settings

    path = Settings().streamable_http_path.strip() or "/"
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
    with_trace_addon: bool = True,
) -> list[str]:
    # Siehe mitmproxy mode_specs: reverse:UPSTREAM@listen_host:listen_port
    up = f"http://127.0.0.1:{backend_port}"
    mode = f"reverse:{up}@127.0.0.1:{front_port}"
    addon = _mitmdump_addon_script()
    cmd: list[str] = [
        mitmdump_exe,
        "--mode",
        mode,
        "--set",
        "flow_detail=0",
    ]
    if with_trace_addon:
        cmd.extend(["-s", str(addon)])
    return cmd


def _tcp_forward_argv(front_port: int, backend_port: int) -> list[str]:
    script = Path(__file__).resolve().parent / "tunnel_front_tcp.py"
    return [sys.executable, str(script), str(front_port), str(backend_port)]


class _ChildProcs:
    cf: subprocess.Popen[str] | None = None
    mitm: subprocess.Popen[str] | None = None
    tcp_forward: subprocess.Popen[str] | None = None
    mitm_log_file: TextIO | None = None
    mcp: subprocess.Popen[str] | None = None


def _bring_up_quick_tunnel_stack(
    mcp_dir: Path,
    port: int,
    mcp_argv: list[str],
    *,
    with_mitmdump: bool,
    echo_mitm_log_path: bool = True,
    cloudflared_diagnostic_sink: Callable[[str], None] | None = None,
    tunnel_split_ports: bool = False,
    mitm_trace: bool = True,
) -> tuple[_ChildProcs, str, int, bool, Path | None]:
    """Startet cloudflared (optional mitm + Warmup-MCP) und liefert öffentliche MCP-URL.

    ``procs.mcp`` ist danach ``None`` (Warmup ggf. beendet). Aufrufer startet den echten MCP.
    Rückgabe ``mitm_log_path`` nur bei mitmdump **mit** Klartext-Trace (``mitm_trace``).

    ``tunnel_split_ports`` (TTY-Supervisor): MCP immer auf ``port+1``; auf ``port`` nur
    mitmdump oder TCP-Forward — so bleibt cloudflared bei Proxy-Umschalten bestehen.
    """
    mitm_log_path: Path | None = None
    cf_exe = ensure_cloudflared()
    mitmdump_exe = shutil.which("mitmdump")
    use_mitm = quick_tunnel_with_mitmdump(
        with_mitmdump=with_mitmdump,
        mitmdump_executable=mitmdump_exe,
    )
    if with_mitmdump and mitmdump_exe is None:
        print(
            "mitmdump nicht im PATH — für ``--http-proxy`` installieren: "
            "brew install mitmproxy (oder pipx install mitmproxy).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if (use_mitm or tunnel_split_ports) and port > _MAX_FRONT_PORT:
        need = port + 1
        msg = f"--port muss ≤ {_MAX_FRONT_PORT} sein (MCP lauscht dann auf {need})."
        print(msg, file=sys.stderr)
        raise SystemExit(1)

    if tunnel_split_ports:
        backend_port = quick_tunnel_backend_port(port)
    else:
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
        _terminate(procs.tcp_forward)
        _close_mitm_log_file(procs)
        _terminate(procs.cf)

    need_warmup = use_mitm or tunnel_split_ports
    if need_warmup:
        procs.mcp = subprocess.Popen(
            _schnappster_mcp_command(mcp_dir, mcp_argv),
            env=_env_for_mcp_tunnel_warmup(backend_port),
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
            w = int(_MCP_BIND_WAIT_S)
            msg = f"MCP (Warmup) lauscht nach {w}s nicht auf 127.0.0.1:{backend_port}."
            print(msg, file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        if use_mitm:
            assert mitmdump_exe is not None
            mitm_fp: TextIO | None = None
            if mitm_trace:
                mitm_log_path, mitm_fp = _open_new_mitmdump_trace_log(mcp_dir)
                procs.mitm_log_file = mitm_fp
                if echo_mitm_log_path:
                    print(
                        f"mitmdump: Klartext-Log → {mitm_log_path.resolve()}",
                        file=sys.stderr,
                        flush=True,
                    )
            mitm_env = os.environ | {"SCHNAPPSTER_MITM_MCP_PATH": _effective_streamable_http_path()}
            if mitm_fp is not None:
                procs.mitm = subprocess.Popen(
                    _mitmdump_reverse_command(
                        mitmdump_exe,
                        front_port=port,
                        backend_port=backend_port,
                        with_trace_addon=True,
                    ),
                    stdin=subprocess.DEVNULL,
                    stdout=mitm_fp,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=mitm_env,
                )
            else:
                procs.mitm = subprocess.Popen(
                    _mitmdump_reverse_command(
                        mitmdump_exe,
                        front_port=port,
                        backend_port=backend_port,
                        with_trace_addon=False,
                    ),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    env=mitm_env,
                )
            time.sleep(0.15)
            if procs.mitm.poll() is not None:
                print("mitmdump sofort beendet — nicht nutzbar.", file=sys.stderr)
                cleanup()
                raise SystemExit(1)
            if not _wait_tcp_accept("127.0.0.1", port, _MITM_LISTEN_WAIT_S):
                print(
                    f"mitmdump lauscht nach {_MITM_LISTEN_WAIT_S:.0f}s nicht auf 127.0.0.1:{port}.",
                    file=sys.stderr,
                )
                cleanup()
                raise SystemExit(1)
        elif tunnel_split_ports:
            procs.tcp_forward = subprocess.Popen(
                _tcp_forward_argv(port, backend_port),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            time.sleep(0.05)
            if procs.tcp_forward.poll() is not None:
                print("TCP-Forward auf dem Front-Port ist sofort beendet.", file=sys.stderr)
                cleanup()
                raise SystemExit(1)
            if not _wait_tcp_accept("127.0.0.1", port, _MITM_LISTEN_WAIT_S):
                w = int(_MITM_LISTEN_WAIT_S)
                print(
                    f"TCP-Forward lauscht nach {w}s nicht auf 127.0.0.1:{port}.",
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
                        stripped = line.rstrip("\n\r")
                        if cloudflared_diagnostic_sink is not None:
                            cloudflared_diagnostic_sink(stripped)
                        else:
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
        if procs.mitm is not None and procs.mitm.poll() is not None:
            print("mitmdump ist während des Tunnel-Starts beendet worden.", file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        if procs.tcp_forward is not None and procs.tcp_forward.poll() is not None:
            print("TCP-Forward ist während des Tunnel-Starts beendet worden.", file=sys.stderr)
            cleanup()
            raise SystemExit(1)
        if procs.mcp is not None and procs.mcp.poll() is not None:
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
    resource_url = f"{public_base}{_effective_streamable_http_path()}"
    if need_warmup:
        _terminate(procs.mcp)
        procs.mcp = None

    return procs, resource_url, backend_port, use_mitm, mitm_log_path


def _close_mitm_log_file(procs: _ChildProcs) -> None:
    if procs.mitm_log_file is None:
        return
    try:
        procs.mitm_log_file.flush()
        procs.mitm_log_file.close()
    except OSError:
        pass
    procs.mitm_log_file = None


def _swap_supervisor_tunnel_front(
    procs: _ChildProcs,
    mcp_dir: Path,
    port: int,
    mcp_argv: list[str],
    *,
    with_mitmdump: bool,
    mitm_trace: bool,
    echo_mitm_log_path: bool,
) -> Path | None:
    """cloudflared in ``procs.cf`` bleibt; Warmup + Front (mitmdump oder TCP-Forward) neu.

    ``mitm_trace`` wirkt nur, wenn ``with_mitmdump`` und mitmdump im PATH.
    """
    mitmdump_exe = shutil.which("mitmdump")
    use_mitm = quick_tunnel_with_mitmdump(
        with_mitmdump=with_mitmdump,
        mitmdump_executable=mitmdump_exe,
    )
    backend_port = quick_tunnel_backend_port(port)
    mitm_log_path: Path | None = None

    def cleanup_front_only() -> None:
        _terminate(procs.mcp)
        procs.mcp = None
        _terminate(procs.mitm)
        procs.mitm = None
        _terminate(procs.tcp_forward)
        procs.tcp_forward = None
        _close_mitm_log_file(procs)

    cleanup_front_only()

    procs.mcp = subprocess.Popen(
        _schnappster_mcp_command(mcp_dir, mcp_argv),
        env=_env_for_mcp_tunnel_warmup(backend_port),
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
        w = int(_MCP_BIND_WAIT_S)
        print(
            f"MCP (Warmup) lauscht nach {w}s nicht auf 127.0.0.1:{backend_port}.",
            file=sys.stderr,
        )
        cleanup_front_only()
        raise SystemExit(1)
    if use_mitm:
        assert mitmdump_exe is not None
        mitm_fp: TextIO | None = None
        if mitm_trace:
            mitm_log_path, mitm_fp = _open_new_mitmdump_trace_log(mcp_dir)
            procs.mitm_log_file = mitm_fp
            if echo_mitm_log_path:
                print(
                    f"mitmdump: Klartext-Log → {mitm_log_path.resolve()}",
                    file=sys.stderr,
                    flush=True,
                )
        mitm_env = os.environ | {"SCHNAPPSTER_MITM_MCP_PATH": _effective_streamable_http_path()}
        if mitm_fp is not None:
            procs.mitm = subprocess.Popen(
                _mitmdump_reverse_command(
                    mitmdump_exe,
                    front_port=port,
                    backend_port=backend_port,
                    with_trace_addon=True,
                ),
                stdin=subprocess.DEVNULL,
                stdout=mitm_fp,
                stderr=subprocess.STDOUT,
                text=True,
                env=mitm_env,
            )
        else:
            procs.mitm = subprocess.Popen(
                _mitmdump_reverse_command(
                    mitmdump_exe,
                    front_port=port,
                    backend_port=backend_port,
                    with_trace_addon=False,
                ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                env=mitm_env,
            )
        time.sleep(0.15)
        if procs.mitm.poll() is not None:
            print("mitmdump sofort beendet — nicht nutzbar.", file=sys.stderr)
            cleanup_front_only()
            raise SystemExit(1)
        if not _wait_tcp_accept("127.0.0.1", port, _MITM_LISTEN_WAIT_S):
            print(
                f"mitmdump lauscht nach {_MITM_LISTEN_WAIT_S:.0f}s nicht auf 127.0.0.1:{port}.",
                file=sys.stderr,
            )
            cleanup_front_only()
            raise SystemExit(1)
    else:
        procs.tcp_forward = subprocess.Popen(
            _tcp_forward_argv(port, backend_port),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        time.sleep(0.05)
        if procs.tcp_forward.poll() is not None:
            print("TCP-Forward auf dem Front-Port ist sofort beendet.", file=sys.stderr)
            cleanup_front_only()
            raise SystemExit(1)
        if not _wait_tcp_accept("127.0.0.1", port, _MITM_LISTEN_WAIT_S):
            w = int(_MITM_LISTEN_WAIT_S)
            print(
                f"TCP-Forward lauscht nach {w}s nicht auf 127.0.0.1:{port}.",
                file=sys.stderr,
            )
            cleanup_front_only()
            raise SystemExit(1)

    _terminate(procs.mcp)
    procs.mcp = None
    return mitm_log_path


def _interactive_cleanup_tunnel_procs(procs: _ChildProcs) -> None:
    _terminate(procs.mcp)
    _terminate(procs.mitm)
    _terminate(procs.tcp_forward)
    _close_mitm_log_file(procs)
    _terminate(procs.cf)


def _ansi_stdout() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR", "").strip()


def _sgr(text: str, *codes: int) -> str:
    if not _ansi_stdout() or not codes:
        return text
    return f"\033[{';'.join(str(c) for c in codes)}m{text}\033[0m"


def _posix_tty_cbreak_supported() -> bool:
    """Unix-TTY: einzelne Tasten ohne Enter (termios + tty.setcbreak)."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        import termios as _termios  # noqa: PLC0415
        import tty as _tty  # noqa: PLC0415
    except ImportError:
        return False
    return hasattr(_termios, "tcgetattr") and hasattr(_tty, "setcbreak")


def run_interactive_supervisor(
    mcp_dir: Path,
    port: int,
    mcp_argv: list[str],
    *,
    use_http_proxy: bool,
) -> None:
    """TTY: Quick-Tunnel, öffentliche URL einmal beim Start, dann MCP-Logs auf stdout.

    Steuerung: ``r`` MCP neu, ``p`` HTTP-Proxy (mitmdump) ein/aus, ``q`` beenden (siehe Start-Box).
    """
    need_tunnel = True
    want_proxy = use_http_proxy
    want_mitm_trace = use_http_proxy
    tunnel_procs: _ChildProcs | None = None
    resource_url: str | None = None
    backend_port = port
    use_mitm = use_http_proxy
    mitm_log_path: Path | None = None

    if need_tunnel:
        (
            tunnel_procs,
            resource_url,
            backend_port,
            use_mitm,
            mitm_log_path,
        ) = _bring_up_quick_tunnel_stack(
            mcp_dir,
            port,
            mcp_argv,
            with_mitmdump=want_proxy,
            echo_mitm_log_path=False,
            cloudflared_diagnostic_sink=_discard_cloudflared_diagnostic,
            tunnel_split_ports=True,
            mitm_trace=want_mitm_trace,
        )
        assert resource_url is not None
        _print_mcp_url_box(resource_url, show_keypad=True)
        if mitm_log_path is not None:
            print(f"mitmdump-Log: {mitm_log_path.resolve()}", flush=True)

    cmd = _schnappster_mcp_command(mcp_dir, mcp_argv)

    def build_child_env() -> dict[str, str]:
        env = dict(os.environ)
        if not need_tunnel:
            env.pop("MCP_RESOURCE_SERVER_URL", None)
            return env
        assert resource_url is not None
        env = env | {"MCP_RESOURCE_SERVER_URL": resource_url}
        if backend_port != port:
            env = env | {"MCP_PORT": str(backend_port)}
        return env

    mcp_child: subprocess.Popen[str] | None = None
    shutting_down = False
    exit_code = 0
    tty_restore: list[tuple[int, object] | None] = [None]

    def restore_tty() -> None:
        pair = tty_restore[0]
        if pair is None:
            return
        fd, old_attrs = pair
        import termios  # noqa: PLC0415

        with contextlib.suppress(OSError):
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        tty_restore[0] = None

    def cleanup_all() -> None:
        nonlocal mcp_child, tunnel_procs
        restore_tty()
        _terminate(mcp_child)
        mcp_child = None
        if tunnel_procs is not None:
            _interactive_cleanup_tunnel_procs(tunnel_procs)
            tunnel_procs = None

    def on_signal(_signum: int, _frame: object | None) -> None:
        cleanup_all()
        sys.exit(128 + _signum)

    def restart_tunnel_stack() -> None:
        """MCP muss bereits gestoppt sein. Front neu oder kompletter Tunnel-Neuaufbau."""
        nonlocal tunnel_procs, resource_url, backend_port, use_mitm, mitm_log_path
        assert tunnel_procs is not None
        cf = tunnel_procs.cf
        if cf is not None and cf.poll() is None:
            mitm_log_path = _swap_supervisor_tunnel_front(
                tunnel_procs,
                mcp_dir,
                port,
                mcp_argv,
                with_mitmdump=want_proxy,
                mitm_trace=want_mitm_trace,
                echo_mitm_log_path=False,
            )
            use_mitm = want_proxy
            backend_port = quick_tunnel_backend_port(port)
            return
        _interactive_cleanup_tunnel_procs(tunnel_procs)
        tunnel_procs = None
        tunnel_procs, resource_url, backend_port, use_mitm, mitm_log_path = (
            _bring_up_quick_tunnel_stack(
                mcp_dir,
                port,
                mcp_argv,
                with_mitmdump=want_proxy,
                echo_mitm_log_path=False,
                cloudflared_diagnostic_sink=_discard_cloudflared_diagnostic,
                tunnel_split_ports=True,
                mitm_trace=want_mitm_trace,
            )
        )

    def apply_proxy_toggle() -> bool:
        """True wenn umgeschaltet; False wenn mitmdump fehlt (``want_proxy`` unverändert)."""
        nonlocal want_proxy
        newv = not want_proxy
        if newv and shutil.which("mitmdump") is None:
            print(
                "mitmdump nicht im PATH — z. B. brew install mitmproxy",
                file=sys.stderr,
            )
            return False
        want_proxy = newv
        cf_ok = (
            tunnel_procs is not None
            and tunnel_procs.cf is not None
            and tunnel_procs.cf.poll() is None
        )
        if cf_ok:
            line = f"[mcp-server] HTTP-Proxy {'an' if want_proxy else 'aus'}"
        else:
            line = f"[mcp-server] HTTP-Proxy {'an' if want_proxy else 'aus'} — Tunnel neu …"
        print(_sgr(line, 2), flush=True)
        restart_tunnel_stack()
        if mitm_log_path is not None:
            print(f"mitmdump-Log: {mitm_log_path.resolve()}", flush=True)
        return True

    def spawn_mcp() -> bool:
        nonlocal mcp_child
        mcp_child = subprocess.Popen(
            cmd,
            env=build_child_env(),
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=subprocess.STDOUT,
            text=True,
        )
        split_ports = backend_port != port
        if split_ports and not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
            print(
                f"MCP lauscht nicht auf 127.0.0.1:{backend_port}.",
                file=sys.stderr,
            )
            return False
        return True

    old_int = signal.signal(signal.SIGINT, on_signal)
    old_term: object | None = None
    if hasattr(signal, "SIGTERM"):
        old_term = signal.signal(signal.SIGTERM, on_signal)

    def stop_mcp_child() -> None:
        nonlocal mcp_child
        if mcp_child is None:
            return
        if mcp_child.poll() is not None:
            with contextlib.suppress(subprocess.TimeoutExpired):
                mcp_child.wait(timeout=_CHILD_TERMINATE_TIMEOUT_S)
            mcp_child = None
            return
        _terminate(mcp_child)
        with contextlib.suppress(subprocess.TimeoutExpired):
            mcp_child.wait(timeout=_CHILD_TERMINATE_TIMEOUT_S)
        mcp_child = None

    try:
        print(_sgr("[mcp-server] Starte schnappster-mcp …", 2), flush=True)
        if not spawn_mcp():
            exit_code = 1
            raise SystemExit(exit_code)

        use_cbreak = _posix_tty_cbreak_supported()
        if use_cbreak:
            import termios  # noqa: PLC0415
            import tty  # noqa: PLC0415

            fd = sys.stdin.fileno()
            tty_restore[0] = (fd, termios.tcgetattr(fd))
            tty.setcbreak(fd)

        while not shutting_down:
            if mcp_child is not None and mcp_child.poll() is not None:
                rc = mcp_child.wait()
                mcp_child = None
                exit_code = int(rc) if rc is not None else 0
                stamp = time.strftime("%H:%M:%S")
                print(
                    _sgr(
                        f"[mcp-server] MCP beendet {stamp} — Exit {exit_code}.  r / p / q",
                        2,
                    ),
                    flush=True,
                )

            if use_cbreak:
                assert tty_restore[0] is not None
                fd = tty_restore[0][0]
                r, _, _ = select.select([fd], [], [], 0.2)
                if not r:
                    continue
                ch = os.read(fd, 1).decode("utf-8", errors="replace")
            else:
                r, _, _ = select.select([sys.stdin], [], [], 0.2)
                if not r:
                    continue
                line = sys.stdin.readline()
                if line == "":
                    shutting_down = True
                    break
                ch = (line.strip()[:1] or "").lower()

            if ch in ("\x03", "\x04", "q", "Q"):
                shutting_down = True
                break

            if ch in ("r", "R"):
                stop_mcp_child()
                print(_sgr("[mcp-server] MCP neu starten …", 2, 33), flush=True)
                if not spawn_mcp():
                    exit_code = 1
                    shutting_down = True
                    break
                print(_sgr("[mcp-server] MCP läuft.", 2, 32), flush=True)
                continue

            if ch in ("p", "P"):
                stop_mcp_child()
                if not apply_proxy_toggle():
                    if not spawn_mcp():
                        exit_code = 1
                        shutting_down = True
                        break
                    continue
                if not spawn_mcp():
                    exit_code = 1
                    shutting_down = True
                    break
                print(_sgr("[mcp-server] MCP ist wieder aktiv.", 2, 32), flush=True)
                continue

    except SystemExit:
        raise
    except KeyboardInterrupt:
        exit_code = 130
    finally:
        signal.signal(signal.SIGINT, old_int)
        if old_term is not None and hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, old_term)
        cleanup_all()

    raise SystemExit(exit_code)


def run_with_quick_tunnel(
    port: int,
    mcp_argv: list[str],
    *,
    with_mitmdump: bool = False,
) -> None:
    mcp_dir = _resolve_mcp_dir()
    procs, resource_url, backend_port, use_mitm, _mitm_log_path = _bring_up_quick_tunnel_stack(
        mcp_dir, port, mcp_argv, with_mitmdump=with_mitmdump
    )

    def cleanup() -> None:
        _interactive_cleanup_tunnel_procs(procs)

    def on_signal(_signum: int, _frame: object | None) -> None:
        cleanup()
        sys.exit(128 + _signum)

    child_env = os.environ | {"MCP_RESOURCE_SERVER_URL": resource_url}
    if backend_port != port:
        child_env = child_env | {"MCP_PORT": str(backend_port)}

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
        split_ports = backend_port != port
        if split_ports and not _wait_tcp_accept("127.0.0.1", backend_port, _MCP_BIND_WAIT_S):
            print(
                f"MCP lauscht nach Setzen der Tunnel-URL nicht auf 127.0.0.1:{backend_port}.",
                file=sys.stderr,
            )
            cleanup()
            raise SystemExit(1)
        _print_mcp_url_box(resource_url, show_keypad=False)
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
            "  uv run mcp-server\n"
            "    Im Terminal: Quick-Tunnel und MCP starten automatisch zusammen.\n"
            "  uv run mcp-server --tunnel\n"
            "    Nur ohne TTY: einmaliger Lauf mit TryCloudflare + MCP.\n"
            "  cloudflared tunnel --url http://127.0.0.1:8766\n"
            "    Nur Tunnel; MCP separat mit „uv run mcp-server“ "
            "(öffentliche URL inkl. Pfad ggf. in .env, siehe .env.example).",
            file=sys.stderr,
        )
        sys.exit(2)

    parser = argparse.ArgumentParser(
        prog="mcp-server",
        description=(
            "Schnappster Remote-MCP: im TTY immer Quick-Tunnel; Steuerung ``r``/``p``/``q``. "
            "``--http-proxy``: mitmdump von Anfang an. "
            "Ohne TTY: einmaliger Start; ``--tunnel`` TryCloudflare + MCP."
        ),
    )
    parser.add_argument(
        "--tunnel",
        "-t",
        action="store_true",
        help=(
            "Nur ohne TTY: einmaliger Start mit TryCloudflare. "
            "Im TTY wird der Tunnel immer gestartet."
        ),
    )
    parser.add_argument(
        "--http-proxy",
        action="store_true",
        help=(
            "mitmdump-Reverse vor dem Tunnel (Klartext-Log unter logs/; "
            "absoluter Pfad beim TTY-Start). Impliziert Quick-Tunnel (wie ``--tunnel``)."
        ),
    )
    parser.add_argument("--port", "-p", type=int, default=8766, metavar="PORT")
    ns, rest = parser.parse_known_args(argv)

    mcp_dir = _resolve_mcp_dir()
    use_http_proxy = ns.http_proxy
    use_tunnel = ns.tunnel or use_http_proxy

    if sys.stdin.isatty():
        run_interactive_supervisor(
            mcp_dir=mcp_dir,
            port=ns.port,
            mcp_argv=rest,
            use_http_proxy=use_http_proxy,
        )
        return

    if use_tunnel:
        run_with_quick_tunnel(
            port=ns.port,
            mcp_argv=rest,
            with_mitmdump=use_http_proxy,
        )
        return

    cmd = _schnappster_mcp_command(mcp_dir, rest)
    env = dict(os.environ)
    env.pop("MCP_RESOURCE_SERVER_URL", None)
    raise SystemExit(subprocess.call(cmd, env=env))
