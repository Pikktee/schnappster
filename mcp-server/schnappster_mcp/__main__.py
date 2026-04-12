"""CLI entry: `uv run schnappster-mcp` or `python -m schnappster_mcp`."""

from typing import Any, cast

from schnappster_mcp.core.config import Settings
from schnappster_mcp.server import build_mcp


def main() -> None:
    """Lädt Einstellungen aus der Umgebung, baut den MCP-Server und startet Streamable HTTP."""
    # `BaseSettings` reads required values from env/.env at runtime.
    # basedpyright still flags direct `Settings()` here as missing arguments.
    settings = cast(Any, Settings)()
    mcp = build_mcp(settings)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
