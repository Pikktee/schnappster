"""Shared fixtures."""

import pytest

from schnappster_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings.model_validate(
        {
            "schnappster_api_base_url": "http://test-api.local",
            "supabase_url": "https://test.supabase.co",
            "supabase_publishable_key": "test-publishable-key",
            "mcp_host": "127.0.0.1",
            "mcp_port": 8766,
            "mcp_resource_server_url": "http://127.0.0.1:8766/mcp",
        }
    )
