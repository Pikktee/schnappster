"""Datenbanktabelle und API-Schemas für Anwendungseinstellungen."""

from sqlmodel import Field, SQLModel


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class AppSettings(SQLModel, table=True):
    """Schlüssel-Wert-Tabelle für Einstellungen
    (z. B. exclude_commercial_sellers, min_seller_rating).
    """

    __tablename__ = "app_settings"  # type: ignore

    key: str = Field(primary_key=True)
    value: str


# -------------------
# --- API-Schemas ---
# -------------------
class AppSettingsRead(SQLModel):
    """API-Ausgabe-Schema für eine einzelne Einstellung."""

    key: str
    value: str


class AppSettingsUpdate(SQLModel):
    """API-Eingabe-Schema zum Aktualisieren eines Einstellungswerts."""

    value: str
