"""Laufzeit-Einstellungen aus der DB: Gewerbe-Ausschluss, Mindest-Verkäuferbewertung, Telegram."""

from sqlmodel import Session

from app.models.settings import AppSettings


class SettingsService:
    """Liest und schreibt Einstellungen aus der Tabelle AppSettings; validiert gegen erlaubte Werte."""

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
        """Erstellt den Service mit der übergebenen Datenbank-Session."""
        self.session = session

    @property
    def supported(self) -> dict:
        """Gibt das Schema aller unterstützten Einstellungsschlüssel und Metadaten zurück."""
        return self._SUPPORTED_SETTINGS.copy()

    def get(self, key: str) -> str:
        """Gibt den String-Wert für einen Einstellungsschlüssel zurück; ValueError bei unbekanntem Schlüssel."""
        if key not in self._SUPPORTED_SETTINGS:
            raise ValueError(f"This setting '{key}' is not supported.")

        config = self.session.get(AppSettings, key)

        return config.value if config else self._SUPPORTED_SETTINGS[key]["default"]

    def get_bool(self, key: str) -> bool:
        """Gibt den Einstellungswert als Boolean zurück (true/false-String)."""
        return self.get(key).lower() == "true"

    def get_int(self, key: str) -> int:
        """Gibt den Einstellungswert als Integer zurück."""
        return int(self.get(key))

    def set(self, key: str, value: str):
        """Setzt einen Einstellungswert; validiert gegen Erlaubtes; legt Zeile an oder aktualisiert sie."""
        if key not in self._SUPPORTED_SETTINGS:
            raise ValueError(f"This setting '{key}' is not supported.")

        # Anhand der Regeln validieren
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
        """Gibt alle unterstützten Einstellungen mit Schlüssel, Wert, Typ, Default, Erlaubtes und Beschreibung zurück."""
        all_settings = []
        for key, details in self._SUPPORTED_SETTINGS.items():
            entry = {
                "key": key,
                "value": self.get(key),
                **details,  # type, default, allowed, description
            }
            all_settings.append(entry)
        return all_settings
