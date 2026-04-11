"""Regex zum Erkennen der TryCloudflare-Basis-URL in cloudflared-Logs."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from schnappster_mcp.cli import (
    _cloudflared_line_is_likely_error,
    _effective_streamable_http_path,
    _env_for_mcp_tunnel_warmup,
    _mitmdump_addon_script,
    _mitmdump_logs_dir,
    _mitmdump_reverse_command,
    extract_trycloudflare_public_base,
    quick_tunnel_backend_port,
    quick_tunnel_with_mitmdump,
)


def test_effective_streamable_http_path_reads_settings_not_only_os_environ() -> None:
    fake = MagicMock()
    fake.streamable_http_path = "/custom-mcp"
    with patch("schnappster_mcp.config.Settings", return_value=fake):
        assert _effective_streamable_http_path() == "/custom-mcp"


def test_effective_streamable_http_path_adds_leading_slash() -> None:
    fake = MagicMock()
    fake.streamable_http_path = "mcp"
    with patch("schnappster_mcp.config.Settings", return_value=fake):
        assert _effective_streamable_http_path() == "/mcp"


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


def test_quick_tunnel_backend_port() -> None:
    assert quick_tunnel_backend_port(8766) == 8767


def test_quick_tunnel_with_mitmdump_rules() -> None:
    assert quick_tunnel_with_mitmdump(
        with_mitmdump=True,
        mitmdump_executable="/x/mitmdump",
    )
    assert not quick_tunnel_with_mitmdump(
        with_mitmdump=False,
        mitmdump_executable="/x/mitmdump",
    )
    assert not quick_tunnel_with_mitmdump(
        with_mitmdump=True,
        mitmdump_executable=None,
    )


def test_mitmdump_logs_dir_next_to_mcp_server() -> None:
    from pathlib import Path

    from schnappster_mcp import cli as cli_mod

    mcp_dir = Path(cli_mod.__file__).resolve().parent.parent
    assert _mitmdump_logs_dir(mcp_dir) == mcp_dir.parent / "logs"


def test_env_for_mcp_tunnel_warmup() -> None:
    env = _env_for_mcp_tunnel_warmup(8767)
    assert env["MCP_PORT"] == "8767"
    assert "MCP_RESOURCE_SERVER_URL" not in env


def test_mitmdump_reverse_command_shape() -> None:
    addon = _mitmdump_addon_script()
    cmd = _mitmdump_reverse_command(
        "/opt/mitmdump",
        front_port=8766,
        backend_port=8767,
    )
    assert cmd[0] == "/opt/mitmdump"
    assert cmd[1] == "--mode"
    assert cmd[2] == "reverse:http://127.0.0.1:8767@127.0.0.1:8766"
    assert cmd[3:7] == ["--set", "flow_detail=0", "-s", str(addon)]
