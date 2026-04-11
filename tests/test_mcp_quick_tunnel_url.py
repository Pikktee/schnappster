"""Regex zum Erkennen der TryCloudflare-Basis-URL in cloudflared-Logs."""

from __future__ import annotations

from schnappster_mcp.cli import _cloudflared_line_is_likely_error, extract_trycloudflare_public_base


def test_extract_trycloudflare_from_typical_log_line() -> None:
    line = "Your quick Tunnel has been created! Visit it at https://abc-12def.trycloudflare.com\n"
    assert extract_trycloudflare_public_base(line) == "https://abc-12def.trycloudflare.com"


def test_extract_trycloudflare_embedded_in_text() -> None:
    line = "INF | https://x-y-1.trycloudflare.com | something else"
    assert extract_trycloudflare_public_base(line) == "https://x-y-1.trycloudflare.com"


def test_extract_trycloudflare_case_insensitive_host() -> None:
    line = "url https://Sub.TryCloudflare.Com/path ignored"
    assert extract_trycloudflare_public_base(line) == "https://Sub.TryCloudflare.Com"


def test_extract_trycloudflare_no_match() -> None:
    assert extract_trycloudflare_public_base("no tunnel here") is None


def test_cloudflared_error_line_detection() -> None:
    assert _cloudflared_line_is_likely_error("2025-01-01T00:00:00Z ERR tunnel failed")
    assert _cloudflared_line_is_likely_error("something FTL something")
    assert not _cloudflared_line_is_likely_error("2025-01-01T00:00:00Z INF Registered tunnel")
