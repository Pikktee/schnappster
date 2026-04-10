"""Anwendungskonfiguration und Projekt-Root-Pfad."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings


def get_app_root() -> Path:
    """Gibt das Projekt-Root-Verzeichnis zurück."""
    return Path(__file__).resolve().parent.parent.parent


class Config(BaseSettings):
    """Anwendungskonfiguration aus Umgebung und .env."""

    database_url: str = f"sqlite:///{get_app_root() / 'data' / 'schnappster.db'}"
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

    # Pydantic-Einstellungen
    model_config = {
        "env_file": get_app_root() / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def validate_required_supabase_admin(self):
        """Im Supabase-Betrieb muss die Primary-Admin-ID gesetzt sein."""
        if self.supabase_url.strip() and not self.primary_admin_user_id.strip():
            raise ValueError("PRIMARY_ADMIN_USER_ID is required when SUPABASE_URL is configured.")
        # Leere CORS-Liste (z. B. CORS_ALLOWED_ORIGINS= in .env) wuerde kein ACAO-Header liefern.
        if not self.cors_allowed_origins.strip():
            self.cors_allowed_origins = "http://localhost:3000,http://127.0.0.1:3000"
        return self


config = Config()
