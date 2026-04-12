"""Environment-backed settings for the MCP server."""

import os
from pathlib import Path
from typing import Self

from pydantic import AliasChoices, AnyHttpUrl, Field, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_AnyHttpUrlAdapter = TypeAdapter(AnyHttpUrl)


def _parse_any_http_url(value: str) -> AnyHttpUrl:
    return _AnyHttpUrlAdapter.validate_python(value)


def _mcp_project_dir() -> Path:
    """Directory `mcp-server/` (parent of package dir `schnappster_mcp/`)."""
    return Path(__file__).resolve().parent.parent


def _dotenv_files() -> tuple[Path, ...]:
    """Load like the main app: repo-root `.env` first, then `mcp-server/.env` (overrides).

    Optional `SCHNAPPSTER_ROOT`: absolute path to the Schnappster repo (for non-standard layouts).
    """
    explicit = os.environ.get("SCHNAPPSTER_ROOT", "").strip()
    if explicit:
        root = Path(explicit).resolve()
        return (root / ".env", _mcp_project_dir() / ".env")

    mcp_dir = _mcp_project_dir()
    candidate_root = mcp_dir.parent
    if (candidate_root / "app").is_dir() and (candidate_root / "pyproject.toml").is_file():
        return (candidate_root / ".env", mcp_dir / ".env")
    return (mcp_dir / ".env",)


class Settings(BaseSettings):
    """Loads from env vars and `.env` files (see `_dotenv_files`)."""

    model_config = SettingsConfigDict(
        env_file=_dotenv_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    schnappster_api_base_url: AnyHttpUrl = Field(
        default_factory=lambda: _parse_any_http_url("http://127.0.0.1:8000"),
        description="Base URL of the Schnappster FastAPI (override in .env for production).",
    )
    supabase_url: AnyHttpUrl = Field(..., description="Supabase project URL")
    supabase_publishable_key: str = Field(..., min_length=1)

    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(
        default=8766,
        validation_alias=AliasChoices("MCP_PORT", "PORT"),
        description="Listen port; Railway/Heroku set PORT, local dev often MCP_PORT.",
    )
    streamable_http_path: str = "/"
    mcp_resource_server_url: AnyHttpUrl | None = Field(
        default=None,
        description=(
            "Public MCP endpoint URL for OAuth metadata (e.g. https://mcp.example.com/ when the "
            "server uses path / on a dedicated host). Defaults to "
            "http://mcp_host:mcp_port/streamable_http_path."
        ),
    )
    log_level: str = "INFO"

    @model_validator(mode="after")
    def default_resource_server_url(self) -> Self:
        if self.mcp_resource_server_url is None:
            path = self.streamable_http_path
            if not path.startswith("/"):
                path = "/" + path
            self.mcp_resource_server_url = _parse_any_http_url(
                f"http://{self.mcp_host}:{self.mcp_port}{path}"
            )
        return self

    @property
    def supabase_auth_issuer_url(self) -> str:
        return f"{str(self.supabase_url).rstrip('/')}/auth/v1"

    @property
    def supabase_user_url(self) -> str:
        return f"{self.supabase_auth_issuer_url}/user"
