"""Runtime settings from DB: commercial exclusion, min seller rating, Telegram."""

from sqlmodel import Session

from app.models.settings import AppSettings


class SettingsService:
    """Read and write app settings stored in AppSettings table; validate against allowed values."""

    _SUPPORTED_SETTINGS: dict[str, dict] = {
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
        "auto_delete_ads_days": {
            "type": "int",
            "default": "7",
            "allowed": ["0", "7", "14", "31"],
            "description": "Alte Anzeigen automatisch löschen nach X Tagen (0 = deaktiviert)",
        },
    }

    def __init__(self, session: Session):
        """Create service with the given database session."""
        self.session = session

    @property
    def supported(self) -> dict:
        """Return schema dict of supported setting keys and metadata."""
        return self._SUPPORTED_SETTINGS.copy()

    def get(self, key: str) -> str:
        """Return the string value for a setting key; raise ValueError if key not supported."""
        if key not in self._SUPPORTED_SETTINGS:
            raise ValueError(f"This setting '{key}' is not supported.")

        config = self.session.get(AppSettings, key)

        return config.value if config else self._SUPPORTED_SETTINGS[key]["default"]

    def get_bool(self, key: str) -> bool:
        """Return the setting value as a boolean (true/false string)."""
        return self.get(key).lower() == "true"

    def get_int(self, key: str) -> int:
        """Return the setting value as an integer."""
        return int(self.get(key))

    def set(self, key: str, value: str):
        """Set a setting value; validate against allowed; create or update AppSettings row."""
        if key not in self._SUPPORTED_SETTINGS:
            raise ValueError(f"This setting '{key}' is not supported.")

        # Validate with rules
        rules = self._SUPPORTED_SETTINGS[key]
        allowed = rules.get("allowed")
        if allowed and value not in allowed:
            raise ValueError(f"Value '{value}' is invalid. Allowed: {', '.join(allowed)}")

        config = self.session.get(AppSettings, key)

        if config:
            config.value = value
        else:
            config = AppSettings(key=key, value=value)
            self.session.add(config)

        self.session.commit()

    def get_all(self) -> list[dict]:
        """Return all supported settings with key, value, type, default, allowed, description."""
        all_settings = []
        for key, details in self._SUPPORTED_SETTINGS.items():
            entry = {
                "key": key,
                "value": self.get(key),
                **details,  # type, default, allowed, description
            }
            all_settings.append(entry)
        return all_settings
