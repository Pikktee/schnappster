from sqlmodel import Session

from app.models.settings import AppSettings

SETTINGS_SCHEMA: dict[str, dict] = {
    "exclude_commercial_sellers": {
        "type": "bool",
        "default": "false",
        "allowed": ["true", "false"],
        "description": "Gewerbliche Verkäufer ausschließen",
    },
    "min_seller_rating": {
        "type": "int",
        "default": "0",
        "allowed": ["0", "1", "2"],
        "description": "Mindest-Verkäuferbewertung (0=Na ja, 1=OK, 2=TOP)",
    },
    "telegram_notifications_enabled": {
        "type": "bool",
        "default": "false",
        "allowed": ["true", "false"],
        "description": "Telegram-Benachrichtigungen bei Schnäppchen",
    },
}


def get_setting(key: str, session: Session) -> str:
    """Get a setting value, falling back to default."""
    if key not in SETTINGS_SCHEMA:
        raise ValueError(f"Unknown setting: {key}")
    config = session.get(AppSettings, key)
    return config.value if config else SETTINGS_SCHEMA[key]["default"]


def get_setting_bool(key: str, session: Session) -> bool:
    """Get a boolean setting."""
    return get_setting(key, session).lower() == "true"


def get_setting_int(key: str, session: Session) -> int:
    """Get an integer setting."""
    return int(get_setting(key, session))


def set_setting(key: str, value: str, session: Session) -> None:
    """Set a setting value with validation."""
    if key not in SETTINGS_SCHEMA:
        raise ValueError(f"Unknown setting: {key}")

    schema = SETTINGS_SCHEMA[key]
    allowed = schema.get("allowed")
    if allowed is not None and value not in allowed:
        raise ValueError(f"Invalid value '{value}' for '{key}'. Allowed: {', '.join(allowed)}")

    config = session.get(AppSettings, key)
    if config:
        config.value = value
    else:
        session.add(AppSettings(key=key, value=value))
    session.commit()


def get_all_settings(session: Session) -> list[dict]:
    """Get all settings with their current values and metadata."""
    result = []
    for key, schema in SETTINGS_SCHEMA.items():
        config = session.get(AppSettings, key)
        result.append(
            {
                "key": key,
                "value": config.value if config else schema["default"],
                "default": schema["default"],
                "type": schema["type"],
                "allowed": schema["allowed"],
                "description": schema["description"],
            }
        )
    return result
