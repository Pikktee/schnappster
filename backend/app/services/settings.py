from sqlmodel import Session

from app.models.settings import AppSettings

REQUIRED_KEYS = ["openrouter_api_key"]

DEFAULTS = {
    "ai_model": "anthropic/claude-sonnet-4-20250514",
    "scrape_interval_minutes": "30",
}


def get_setting(key: str, session: Session) -> str | None:
    config = session.get(AppSettings, key)
    return config.value if config else DEFAULTS.get(key)


def is_setup_complete(session: Session) -> bool:
    for key in REQUIRED_KEYS:
        value = get_setting(key, session)
        if not value:
            return False
    return True
