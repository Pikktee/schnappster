"""Datenbanktabelle und API-Schemas fuer nutzerbezogene Einstellungen."""

import unicodedata

from pydantic import field_validator
from sqlmodel import Field, SQLModel


def normalize_display_name_for_api(value: str) -> str:
    """Strippt und verlangt mindestens ein Unicode-Buchstabe (Kategorie L*)."""
    stripped = (value or "").strip()
    if not any(unicodedata.category(ch).startswith("L") for ch in stripped):
        msg = (
            "Der Name muss mindestens einen Buchstaben enthalten "
            "(Leerzeichen am Rand zählen nicht)."
        )
        raise ValueError(msg)
    return stripped


class UserSettings(SQLModel, table=True):
    """Persoenliche Einstellungen pro User."""

    __tablename__ = "user_settings"  # type: ignore

    user_id: str = Field(primary_key=True)
    display_name: str = ""
    display_name_user_set: bool = Field(default=False)
    telegram_chat_id: str | None = None
    notify_telegram: bool = False
    notify_min_score: int = Field(default=8, ge=0, le=10)
    deletion_pending: bool = False


class UserSettingsRead(SQLModel):
    """API-Ausgabe fuer die persoenlichen Settings."""

    user_id: str
    display_name: str
    telegram_chat_id: str | None
    notify_telegram: bool
    notify_min_score: int
    deletion_pending: bool


class UserSettingsUpdate(SQLModel):
    """Partielles Update fuer persoenliche Settings."""

    display_name: str | None = None
    telegram_chat_id: str | None = None
    notify_telegram: bool | None = None
    notify_min_score: int | None = Field(default=None, ge=0, le=10)

    @field_validator("display_name", mode="before")
    @classmethod
    def validate_display_name_when_set(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_display_name_for_api(value)


class UserProfileRead(SQLModel):
    """Profil-Read-Modell fuer /users/me."""

    id: str
    email: str | None
    display_name: str
    avatar_url: str | None
    role: str


class UserProfileUpdate(SQLModel):
    """Profil-Update, derzeit nur display_name."""

    display_name: str = Field(..., max_length=50)

    @field_validator("display_name", mode="before")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return normalize_display_name_for_api(value)
