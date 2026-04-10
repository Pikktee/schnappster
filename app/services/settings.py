"""Laufzeit-Einstellungen aus der DB: global und pro User."""

from sqlmodel import Session

from app.models.settings_app import AppSettings
from app.models.settings_user import UserSettings, UserSettingsUpdate


class SettingsService:
    """Liest/schreibt AppSettings und validiert gegen erlaubte Werte."""

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
        """Gibt den String-Wert eines Schluessels zurueck.

        Wirft ValueError bei unbekanntem Schluessel.
        """
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
        """Setzt einen Einstellungswert.

        Validiert gegen erlaubte Werte und legt die Zeile bei Bedarf an.
        """
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
        """Gibt alle unterstuetzten Einstellungen inkl. Metadaten zurueck."""
        all_settings = []
        for key, details in self._SUPPORTED_SETTINGS.items():
            entry = {
                "key": key,
                "value": self.get(key),
                **details,  # type, default, allowed, description
            }
            all_settings.append(entry)
        return all_settings

    def get_user_settings(self, user_id: str, default_display_name: str = "") -> UserSettings:
        """Liefert UserSettings; legt sie bei Bedarf mit Defaults an."""
        user_settings = self.session.get(UserSettings, user_id)
        if user_settings:
            return user_settings
        user_settings = UserSettings(
            user_id=user_id,
            display_name=(default_display_name or "").strip(),
            display_name_user_set=False,
        )
        self.session.add(user_settings)
        self.session.commit()
        self.session.refresh(user_settings)
        return user_settings

    def hydrate_display_name_from_identity(
        self,
        user_id: str,
        identity_display_name: str,
    ) -> UserSettings:
        """Provider-Namen in die DB schreiben, solange der Nutzer keinen eigenen Namen gesetzt hat.

        Google-Namen u. a. werden nachgezogen, ohne eine bewusst leere Eingabe zu ueberschreiben.
        """
        identity_display_name = (identity_display_name or "").strip()
        settings = self.get_user_settings(user_id, default_display_name=identity_display_name)
        if settings.display_name_user_set:
            return settings
        if identity_display_name and not (settings.display_name or "").strip():
            settings.display_name = identity_display_name
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
        return settings

    def update_user_settings(self, user_id: str, data: UserSettingsUpdate) -> UserSettings:
        """Aktualisiert UserSettings partiell."""
        settings = self.get_user_settings(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "display_name" in update_data:
            settings.display_name_user_set = True
        for key, value in update_data.items():
            if key == "display_name" and value is None:
                value = ""
            setattr(settings, key, value)
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings
