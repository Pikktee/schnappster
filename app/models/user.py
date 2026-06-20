"""Datenbanktabelle und API-Schemas fuer Benutzerkonten (eigene Auth)."""

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import field_validator
from sqlmodel import Field, SQLModel


def _new_user_id() -> str:
    """Erzeugt eine zufaellige User-ID (UUID4 als String)."""
    return str(uuid4())


def normalize_email(value: str) -> str:
    """Trimmt, kleinschreibt und prueft minimal auf ein '@' mit Domain."""
    email = (value or "").strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise ValueError("Bitte eine gueltige E-Mail-Adresse eingeben.")
    return email


# ------------------------
# --- Datenbanktabelle ---
# ------------------------
class User(SQLModel, table=True):
    """Benutzerkonto mit lokalem Passwort-Hash."""

    __tablename__ = "users"  # type: ignore

    id: str = Field(default_factory=_new_user_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="user")  # "user" | "admin"
    is_active: bool = Field(default=False)
    display_name: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# -------------------
# --- API-Schemas ---
# -------------------
class UserRead(SQLModel):
    """Ausgabe fuer die Admin-Benutzerverwaltung."""

    id: str
    email: str
    role: str
    is_active: bool
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterRequest(SQLModel):
    """Selbstregistrierung (Konto bleibt bis zur Freischaltung inaktiv)."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str) -> str:
        return normalize_email(value)


class LoginRequest(SQLModel):
    """Login mit E-Mail und Passwort."""

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(SQLModel):
    """Antwort des Login-Endpunkts."""

    access_token: str
    token_type: str = "bearer"


class AdminUserCreate(SQLModel):
    """Admin legt ein (i. d. R. bereits aktives) Konto an."""

    email: str
    password: str
    role: str = "user"
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str) -> str:
        return normalize_email(value)


class AdminUserUpdate(SQLModel):
    """Admin schaltet frei/sperrt oder aendert die Rolle."""

    is_active: bool | None = None
    role: str | None = None

    @field_validator("role")
    @classmethod
    def _check_role(cls, value: str | None) -> str | None:
        if value is not None and value not in {"user", "admin"}:
            raise ValueError("Rolle muss 'user' oder 'admin' sein.")
        return value


class AdminPasswordReset(SQLModel):
    """Admin setzt ein neues Passwort fuer einen Benutzer."""

    new_password: str
