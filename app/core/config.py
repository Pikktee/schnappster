from pathlib import Path

from pydantic_settings import BaseSettings


def get_app_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


class Config(BaseSettings):
    database_url: str = f"sqlite:///{get_app_root() / 'data' / 'schnappster.db'}"
    openrouter_api_key: str = ""
    openrouter_ai_model: str = "google/gemini-2.0-flash-001"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    model_config = {
        "env_file": get_app_root() / ".env",
        "env_file_encoding": "utf-8",
    }


config = Config()
