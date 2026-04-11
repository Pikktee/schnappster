"""Transport security: allow public MCP host (tunnel) with loopback bind."""

from schnappster_mcp.server import _transport_security


def test_transport_security_includes_trycloudflare_host() -> None:
    from schnappster_mcp.config import Settings

    s = Settings.model_validate(
        {
            "schnappster_api_base_url": "http://127.0.0.1:8000",
            "supabase_url": "https://x.supabase.co",
            "supabase_publishable_key": "k",
            "mcp_host": "127.0.0.1",
            "mcp_port": 8766,
            "mcp_resource_server_url": "https://abc.trycloudflare.com/",
        }
    )
    ts = _transport_security(s)
    assert ts is not None
    assert ts.enable_dns_rebinding_protection is True
    assert "abc.trycloudflare.com" in ts.allowed_hosts
    assert any("trycloudflare.com" in o for o in ts.allowed_origins)


def test_transport_security_none_for_non_loopback_bind() -> None:
    from schnappster_mcp.config import Settings

    s = Settings.model_validate(
        {
            "schnappster_api_base_url": "http://127.0.0.1:8000",
            "supabase_url": "https://x.supabase.co",
            "supabase_publishable_key": "k",
            "mcp_host": "0.0.0.0",
            "mcp_port": 8766,
            "mcp_resource_server_url": "https://abc.trycloudflare.com/",
        }
    )
    assert _transport_security(s) is None
