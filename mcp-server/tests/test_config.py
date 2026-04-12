"""Settings defaults."""

import pytest

from schnappster_mcp.core.config import Settings


def test_default_resource_server_url_from_host_port() -> None:
    """Ohne explizite Resource-URL wird ``http://mcp_host:mcp_port/`` abgeleitet."""
    s = Settings.model_validate(
        {
            "schnappster_api_base_url": "http://localhost:8000",
            "supabase_url": "https://x.supabase.co",
            "supabase_publishable_key": "k",
            "mcp_host": "127.0.0.1",
            "mcp_port": 9999,
            "mcp_resource_server_url": None,
        }
    )
    assert str(s.mcp_resource_server_url) == "http://127.0.0.1:9999/"


def test_mcp_port_from_port_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Umgebungsvariable ``PORT`` setzt ``mcp_port``, wenn ``MCP_PORT`` fehlt."""
    monkeypatch.setenv("PORT", "3000")
    monkeypatch.delenv("MCP_PORT", raising=False)
    s = Settings.model_validate(
        {
            "supabase_url": "https://x.supabase.co",
            "supabase_publishable_key": "k",
        }
    )
    assert s.mcp_port == 3000


def test_mcp_port_prefers_mcp_port_over_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """``MCP_PORT`` hat Vorrang vor ``PORT``."""
    monkeypatch.setenv("PORT", "3000")
    monkeypatch.setenv("MCP_PORT", "8767")
    s = Settings.model_validate(
        {
            "supabase_url": "https://x.supabase.co",
            "supabase_publishable_key": "k",
        }
    )
    assert s.mcp_port == 8767
