"""mitmproxy-Addon für ``mitmdump -s …`` (von ``uv run mcp-server --http-proxy``): MCP-/mcp-Flows mit Body + redaktierter Authorization.

Wird von ``mcp-server --tunnel`` gestartet; Pfad zu ``SCHNAPPSTER_MITM_MCP_PATH``
(z. B. ``/`` oder ``/mcp``).
"""

from __future__ import annotations

import json
import os
from typing import Any

from mitmproxy import http

_MAX_BODY_CHARS = 200_000


def _mcp_path_prefix() -> str:
    raw = (os.environ.get("SCHNAPPSTER_MITM_MCP_PATH") or "/").strip() or "/"
    return raw if raw.startswith("/") else f"/{raw}"


def _redacted_header_lines(headers: http.Headers) -> list[str]:
    lines: list[str] = []
    for name, value in headers.fields:
        k = name.decode(errors="replace")
        v = value.decode(errors="replace")
        if k.lower() == "authorization":
            v = "***redacted***"
        lines.append(f"    {k}: {v}")
    return lines


def _body_preview(content: bytes | None) -> str:
    if not content:
        return "    <empty>"
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return f"    <binary {len(content)} bytes>"
    if len(text) > _MAX_BODY_CHARS:
        text = text[:_MAX_BODY_CHARS] + "\n    … truncated …"
    try:
        parsed: Any = json.loads(text)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        return "\n".join(f"    {line}" for line in pretty.splitlines())
    except (json.JSONDecodeError, TypeError, ValueError):
        return "\n".join(f"    {line}" for line in text.splitlines())


def _request_matches_mcp_path(request_path: str, prefix: str) -> bool:
    """Root ``/`` darf nicht jeden Pfad matchen (würde sonst alles loggen)."""
    if prefix == "/":
        return request_path in ("/", "")
    return request_path.startswith(prefix)


class McpTunnelTrace:
    def __init__(self) -> None:
        self._prefix = _mcp_path_prefix()

    def response(self, flow: http.HTTPFlow) -> None:
        req = flow.request
        if not _request_matches_mcp_path(req.path, self._prefix):
            return
        parts: list[str] = [
            "",
            "── MCP (Klartext) ───────────────────────────────────────────",
            f"{req.method} {req.pretty_url}",
            "  Request headers:",
            *_redacted_header_lines(req.headers),
            "  Request body:",
            _body_preview(req.raw_content),
        ]
        if flow.response:
            res = flow.response
            parts.extend(
                [
                    f"  << {res.status_code} {res.reason}",
                    "  Response headers:",
                    *_redacted_header_lines(res.headers),
                    "  Response body:",
                    _body_preview(res.raw_content),
                ]
            )
        parts.append("── end MCP ──────────────────────────────────────────────────")
        print("\n".join(parts), flush=True)


addons = [McpTunnelTrace()]
