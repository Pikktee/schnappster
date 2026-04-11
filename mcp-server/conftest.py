"""Gemeinsame pytest-Fixtures für `mcp-server/tests/`.

Liegt unter `mcp-server/` (nicht unter `tests/`), damit beim Sammeln mit dem
Root-`tests/`-Baum kein zweites Modul ``tests.conftest`` entsteht.
"""

from __future__ import annotations

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
            "mcp_resource_server_url": "http://127.0.0.1:8766/",
        }
    )
