"""Anwendungskonfiguration und Projekt-Root-Pfad."""

from pathlib import Path

from pydantic_settings import BaseSettings


def get_app_root() -> Path:
    """Gibt das Projekt-Root-Verzeichnis zurück."""
    return Path(__file__).resolve().parent.parent.parent


class Config(BaseSettings):
    """Anwendungskonfiguration aus Umgebung und .env."""

    database_url: str = f"sqlite:///{get_app_root() / 'data' / 'schnappster.db'}"
    openai_api_key: str = ""
    openai_model: str = "google/gemini-2.0-flash-001"
    openai_base_url: str = "https://openrouter.ai/api/v1"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Pydantic-Einstellungen
    model_config = {
        "env_file": get_app_root() / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


config = Config()
