"""CLI entry: `uv run schnappster-mcp` or `python -m schnappster_mcp`."""

from typing import Any, cast

from schnappster_mcp.config import Settings
from schnappster_mcp.server import build_mcp


def main() -> None:
    # `BaseSettings` reads required values from env/.env at runtime.
    # basedpyright still flags direct `Settings()` here as missing arguments.
    settings = cast(Any, Settings)()
    mcp = build_mcp(settings)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
