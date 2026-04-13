"""Temporäre Runtime-Debug-Logs (NDJSON) für Cursor-Debug-Session."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEBUG_LOG_PATH = Path("/Users/henrik/Dev/schnappster/.cursor/debug-c4423a.log")
_SESSION_ID = "c4423a"


def write_debug_log(
    *,
    run_id: str,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
) -> None:
    payload = {
        "sessionId": _SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": __import__("time").time_ns() // 1_000_000,
    }
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
