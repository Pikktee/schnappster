"""Anwendungskonfiguration und Projekt-Root-Pfad."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


def get_app_root() -> Path:
    """Gibt das Projekt-Root-Verzeichnis zurück."""
    return Path(__file__).resolve().parent.parent.parent


_DEFAULT_SQLITE_PATH = get_app_root() / "data" / "schnappster.db"
_DEFAULT_CORS = "http://localhost:3000,http://127.0.0.1:3000"


class Config(BaseSettings):
    """Anwendungskonfiguration aus Umgebung und .env."""

    database_url: str = Field(
        default=f"sqlite:///{_DEFAULT_SQLITE_PATH}",
        description="SQLAlchemy-DB-URL (Default: lokale SQLite-Datei unter data/).",
    )
    jwt_secret: str = Field(
        ...,
        description="Secret zum Signieren der Auth-JWTs (HS256). Zwingend setzen.",
    )
    access_token_expire_minutes: int = Field(default=10_080, ge=1)  # 7 Tage
    admin_email: str = ""
    admin_password: str = ""
    cors_allowed_origins: str = _DEFAULT_CORS
    cors_allowed_origin_regex: str = ""
    openai_api_key: str = ""
    openai_model: str = "openai/gpt-5.4-mini"
    openai_cheap_model: str = "openai/gpt-5.4-nano"
    openai_base_url: str = "https://openrouter.ai/api/v1"
    telegram_bot_token: str = ""
    scrape_request_timeout: float = 20.0
    ai_request_timeout: float = 45.0
    ai_max_comparison_candidates: int = Field(default=12, ge=0, le=30)
    ai_strong_model_min_delta_percent: float = Field(default=18.0, ge=0, le=100)
    ai_strong_model_min_savings_eur: float = Field(default=75.0, ge=0)

    # Pydantic-Einstellungen
    model_config = {
        "env_file": get_app_root() / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("database_url")
    @classmethod
    def supported_db_url(cls, value: str) -> str:
        """Erlaubt SQLite (Default) und PostgreSQL."""
        url = value.strip()
        if not (url.startswith("sqlite") or url.startswith("postgresql")):
            raise ValueError(
                "DATABASE_URL must be a SQLite URL (e.g. sqlite:///./data/schnappster.db) "
                "or a PostgreSQL URL (e.g. postgresql+psycopg://user:pass@host:5432/db)."
            )
        return url

    @field_validator("cors_allowed_origins")
    @classmethod
    def default_cors_when_empty(cls, value: str) -> str:
        """Leere CORS-Liste (z. B. CORS_ALLOWED_ORIGINS= in .env) auf Default zurücksetzen."""
        return value.strip() or _DEFAULT_CORS


config = Config()  # pyright: ignore[reportCallIssue] — Felder aus Umgebung / .env
