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
    openai_cheap_model: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    telegram_bot_token: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 10
    db_connect_timeout: int = 5
    db_statement_timeout_ms: int = 30_000
    supabase_auth_timeout: float = 5.0
    supabase_auth_cache_ttl: float = 60.0
    scrape_request_timeout: float = 20.0
    ai_request_timeout: float = 45.0
    ai_max_comparison_candidates: int = Field(default=12, ge=0, le=30)
    ai_strong_model_min_delta_percent: float = Field(default=18.0, ge=0, le=100)
    ai_strong_model_min_savings_eur: float = Field(default=75.0, ge=0)
    ai_include_images: bool = False

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
        return self


config = Config()  # pyright: ignore[reportCallIssue] — Felder aus Umgebung / .env
