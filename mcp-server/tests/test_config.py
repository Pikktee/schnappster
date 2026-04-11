"""Settings defaults."""

from schnappster_mcp.config import Settings


def test_default_resource_server_url_from_host_port() -> None:
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
