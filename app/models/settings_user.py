"""Datenbanktabelle und API-Schemas fuer nutzerbezogene Einstellungen."""

from sqlmodel import Field, SQLModel


class UserSettings(SQLModel, table=True):
    """Persoenliche Einstellungen pro User."""

    __tablename__ = "user_settings"  # type: ignore

    user_id: str = Field(primary_key=True)
    display_name: str = ""
    display_name_user_set: bool = Field(default=False)
    telegram_chat_id: str | None = None
    notify_telegram: bool = False
    notify_email: bool = False
    notify_min_score: int = Field(default=8, ge=0, le=10)
    deletion_pending: bool = False


class UserSettingsRead(SQLModel):
    """API-Ausgabe fuer die persoenlichen Settings."""

    user_id: str
    display_name: str
    telegram_chat_id: str | None
    notify_telegram: bool
    notify_email: bool
    notify_min_score: int
    deletion_pending: bool


class UserSettingsUpdate(SQLModel):
    """Partielles Update fuer persoenliche Settings."""

    display_name: str | None = None
    telegram_chat_id: str | None = None
    notify_telegram: bool | None = None
    notify_email: bool | None = None
    notify_min_score: int | None = Field(default=None, ge=0, le=10)


class UserProfileRead(SQLModel):
    """Profil-Read-Modell fuer /users/me."""

    id: str
    email: str | None
    display_name: str
    avatar_url: str | None
    role: str


class UserProfileUpdate(SQLModel):
    """Profil-Update, derzeit nur display_name."""

    display_name: str = Field(default="", max_length=50)
