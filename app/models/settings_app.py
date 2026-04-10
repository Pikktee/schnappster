"""Datenbanktabelle und API-Schemas fuer globale Anwendungseinstellungen."""

from sqlmodel import Field, SQLModel


class AppSettings(SQLModel, table=True):
    """Schluessel-Wert-Tabelle fuer globale Einstellungen."""

    __tablename__ = "app_settings"  # type: ignore

    key: str = Field(primary_key=True)
    value: str


class AppSettingsRead(SQLModel):
    """API-Ausgabe-Schema fuer eine einzelne Einstellung."""

    key: str
    value: str


class AppSettingsUpdate(SQLModel):
    """API-Eingabe-Schema zum Aktualisieren eines Einstellungswerts."""

    value: str
