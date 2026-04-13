"""Anwendungskonfiguration und Projekt-Root-Pfad."""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


def get_app_root() -> Path:
    """Gibt das Projekt-Root-Verzeichnis zurück."""
    return Path(__file__).resolve().parent.parent.parent


class Config(BaseSettings):
    """Anwendungskonfiguration aus Umgebung und .env."""

    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL (e.g. postgresql+psycopg://user:pass@host:5432/db)",
    )
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    primary_admin_user_id: str = ""
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_allowed_origin_regex: str = ""
    openai_api_key: str = ""
    openai_model: str = "google/gemini-2.0-flash-001"
    openai_base_url: str = "https://openrouter.ai/api/v1"
    telegram_bot_token: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 2
    db_pool_timeout: int = 20
    db_connect_timeout: int = 3
    db_pool_recycle: int = 300

    # Pydantic-Einstellungen
    model_config = {
        "env_file": get_app_root() / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        """Nur PostgreSQL (lokal, Supabase Pooler, …)."""
        url = value.strip()
        if not url.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL, e.g. postgresql+psycopg://user:pass@host:5432/db"
            )
        return url

    @model_validator(mode="after")
    def validate_required_supabase_admin(self):
        """Im Supabase-Betrieb muss die Primary-Admin-ID gesetzt sein."""
        if self.supabase_url.strip() and not self.primary_admin_user_id.strip():
            raise ValueError("PRIMARY_ADMIN_USER_ID is required when SUPABASE_URL is configured.")
        # Leere CORS-Liste (z. B. CORS_ALLOWED_ORIGINS= in .env) wuerde kein ACAO-Header liefern.
        if not self.cors_allowed_origins.strip():
            self.cors_allowed_origins = "http://localhost:3000,http://127.0.0.1:3000"
        self.db_pool_size = max(self.db_pool_size, 1)
        self.db_max_overflow = max(self.db_max_overflow, 0)
        self.db_pool_timeout = max(self.db_pool_timeout, 1)
        self.db_connect_timeout = max(self.db_connect_timeout, 1)
        self.db_pool_recycle = max(self.db_pool_recycle, 60)
        return self


config = Config()  # pyright: ignore[reportCallIssue] — Felder aus Umgebung / .env
