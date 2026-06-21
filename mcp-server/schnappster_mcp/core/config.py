"""Environment-backed settings for the MCP server."""

import os
from pathlib import Path
from typing import Self
from urllib.parse import urlparse

from pydantic import AliasChoices, AnyHttpUrl, Field, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_AnyHttpUrlAdapter = TypeAdapter(AnyHttpUrl)


def _parse_any_http_url(value: str) -> AnyHttpUrl:
    """Parst einen String zu ``AnyHttpUrl`` (gleiche Regeln wie Pydantic)."""
    return _AnyHttpUrlAdapter.validate_python(value)


def _mcp_project_dir() -> Path:
    """Directory `mcp-server/` (parent of package dir `schnappster_mcp/`)."""
    return Path(__file__).resolve().parent.parent.parent


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
        """Setzt ``mcp_resource_server_url`` aus Host, Port und Streamable-HTTP-Pfad, falls leer."""
        if self.mcp_resource_server_url is None:
            path = self.streamable_http_path
            if not path.startswith("/"):
                path = "/" + path
            self.mcp_resource_server_url = _parse_any_http_url(
                f"http://{self.mcp_host}:{self.mcp_port}{path}"
            )
        return self

    @property
    def api_base_url(self) -> str:
        """Basis-URL der Schnappster-API (ohne abschliessenden Slash)."""
        return str(self.schnappster_api_base_url).rstrip("/")

    @property
    def users_me_url(self) -> str:
        """URL fuer ``GET /users/me/`` zur Token-Validierung gegen die Schnappster-API."""
        return f"{self.api_base_url}/users/me/"

    @property
    def login_url(self) -> str:
        """URL fuer ``POST /auth/login`` (E-Mail/Passwort-Pruefung beim OAuth-Login)."""
        return f"{self.api_base_url}/auth/login"

    @property
    def mcp_issuer_url(self) -> str:
        """OAuth-Issuer: der mcp-server selbst (Origin der oeffentlichen MCP-URL).

        Der mcp-server ist der Authorization-Server; ``/authorize``, ``/token`` und die
        AS-Metadata liegen hier, nicht in der Haupt-API.
        """
        assert self.mcp_resource_server_url is not None
        parsed = urlparse(str(self.mcp_resource_server_url))
        port = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"
