"""Deal-Alarm-Modelle (MyDealz-Schlagwort-Watcher) und API-Schemas.

Kein Kaufziel wie AdSearch — ein Deal-Alarm überwacht einen Suchbegriff auf einer Community-
Deal-Seite (MyDealz) und benachrichtigt bei neuen Deals über einer optionalen **Temperatur**-
Schwelle. Die Community-Temperatur ersetzt die KI-Bewertung.
"""

from datetime import UTC, datetime

from pydantic import field_validator
from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

DEFAULT_DEAL_INTERVAL_MINUTES = 30
MIN_DEAL_INTERVAL_MINUTES = 15
DEFAULT_DEAL_SOURCE = "mydealz"


# ------------------------
# --- Datenbanktabellen ---
# ------------------------
class DealWatch(SQLModel, table=True):
    """Überwacht einen Suchbegriff auf einer Deal-Community-Seite (aktuell MyDealz)."""

    __tablename__ = "deal_watches"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    name: str
    # Suchbegriff, auf den überwacht wird (z. B. "lego millennium falcon").
    query: str
    # Quelle/Community-Seite; aktuell nur MyDealz, aber erweiterbar gehalten.
    source: str = Field(default=DEFAULT_DEAL_SOURCE)
    # Optionale Temperatur-Schwelle (Grad): nur Deals darüber lösen einen Alarm aus.
    min_temperature: float | None = None
    # Optionale Aufheiz-Schwelle (Grad/Stunde): Deals, die schneller steigen, lösen einen Alarm aus.
    min_heating_velocity: float | None = None
    scrape_interval_minutes: int = DEFAULT_DEAL_INTERVAL_MINUTES
    is_active: bool = True
    last_checked_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    deals: list["Deal"] = Relationship(
        back_populates="deal_watch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Deal(SQLModel, table=True):
    """Ein auf einem Deal-Alarm gefundener Deal (dedupliziert über deal_watch_id + external_id)."""

    __tablename__ = "deals"  # type: ignore
    __table_args__ = (Index("idx_deals_watch_external", "deal_watch_id", "external_id"),)

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    deal_watch_id: int = Field(foreign_key="deal_watches.id", ondelete="CASCADE", index=True)
    external_id: str = Field(index=True)
    title: str
    url: str
    temperature: float | None = None
    price: float | None = None
    next_best_price: float | None = None
    merchant: str | None = None
    # Fertige CDN-Bild-URL des Deals (aus MyDealz mainImage gebaut).
    image_url: str | None = None
    # Unix-Zeitstempel der Veröffentlichung auf MyDealz.
    published_at: int | None = None
    # Unix-Zeitstempel, zu dem der Deal heiß wurde; published_at→hot_date = Zeit bis heiß.
    hot_date: int | None = None
    # Selbst gemessene Aufheizung: aktuelle Temperatur + Vormessung mit Zeitstempeln.
    # Erhitzungsgeschwindigkeit (°/h) = (temperature − previous_temperature) / Δt.
    temperature_updated_at: datetime | None = None
    previous_temperature: float | None = None
    previous_temperature_at: datetime | None = None
    # Ob für diesen Deal bereits benachrichtigt wurde (Baseline beim ersten Check → False).
    notified: bool = False
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

    deal_watch: "DealWatch" = Relationship(back_populates="deals")


# -------------------
# --- API-Schemas ---
# -------------------
class DealWatchCreate(SQLModel):
    """API-Eingabe zum Anlegen eines Deal-Alarms."""

    name: str = ""
    query: str
    min_temperature: float | None = None
    min_heating_velocity: float | None = None
    scrape_interval_minutes: int = DEFAULT_DEAL_INTERVAL_MINUTES
    is_active: bool = True

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Bitte einen Suchbegriff für den Deal-Alarm angeben.")
        return v.strip()

    @field_validator("min_heating_velocity")
    @classmethod
    def validate_velocity(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Die Aufheiz-Schwelle darf nicht negativ sein.")
        return v

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_DEAL_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_DEAL_INTERVAL_MINUTES} Minuten betragen."
            )
        return v

    @field_validator("min_temperature")
    @classmethod
    def validate_temperature(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Die Temperatur-Schwelle darf nicht negativ sein.")
        return v


class DealWatchRead(SQLModel):
    """API-Ausgabe für einen Deal-Alarm."""

    id: int
    owner_id: str
    name: str
    query: str
    source: str
    min_temperature: float | None
    min_heating_velocity: float | None
    scrape_interval_minutes: int
    is_active: bool
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime


class DealWatchUpdate(SQLModel):
    """API-Eingabe für Teilaktualisierungen (Name, Schwelle, Intervall, Aktiv-Status)."""

    name: str | None = None
    min_temperature: float | None = None
    min_heating_velocity: float | None = None
    scrape_interval_minutes: int | None = None
    is_active: bool | None = None

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v < MIN_DEAL_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_DEAL_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class DealRead(SQLModel):
    """API-Ausgabe für einen gefundenen Deal."""

    id: int
    external_id: str
    title: str
    url: str
    temperature: float | None
    price: float | None
    next_best_price: float | None
    merchant: str | None
    image_url: str | None
    published_at: int | None
    hot_date: int | None
    # Gemessene Erhitzungsgeschwindigkeit in Grad/Stunde (im Route-Handler berechnet).
    heating_velocity: float | None = None
    first_seen_at: datetime


class DealWatchPreviewRequest(SQLModel):
    """Eingabe für den /preview-Endpoint: nur der Suchbegriff."""

    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Bitte einen Suchbegriff angeben.")
        return v.strip()


class DealPreview(SQLModel):
    """Ein Deal-Vorschlag in der Vorschau (vor dem Anlegen)."""

    external_id: str
    title: str
    url: str
    temperature: float | None
    price: float | None
    next_best_price: float | None
    merchant: str | None
    image_url: str | None


class DealWatchPreviewResponse(SQLModel):
    """Antwort des /preview-Endpoints: aktuell gefundene Deals zum Suchbegriff."""

    deals: list[DealPreview]
