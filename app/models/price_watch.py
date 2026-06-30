"""Preis-Alarm-Modelle (generisches Webseiten-Preis-Monitoring) und API-Schemas."""

from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import field_validator
from sqlalchemy import Column, Index
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

# Minimal-Intervall: schont Zielseiten und reduziert Bot-Detection.
MIN_PRICE_INTERVAL_MINUTES = 30
DEFAULT_PRICE_INTERVAL_MINUTES = 360


def _validate_http_url(url: str) -> str:
    """Stellt sicher, dass die URL eine gültige http(s)-Adresse mit Host ist."""
    cleaned = (url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            "Bitte eine gültige Webadresse eingeben (beginnend mit http:// oder https://)."
        )
    return cleaned


# ------------------------
# --- Datenbanktabellen ---
# ------------------------
class PriceWatch(SQLModel, table=True):
    """Überwacht eine beliebige Webseite auf Preisänderungen."""

    __tablename__ = "price_watches"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    name: str
    url: str
    # Erkannte Währung (z.B. "EUR", "USD"); rein informativ für die Anzeige.
    currency: str | None = None
    # Extraktions-Strategie zur Wiederfindung des Preises (jsonld/meta/css). JSON-Spalte.
    locator: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # Nutzerfreundliches Label der gewählten Preisangabe (z.B. "Aktueller Preis").
    selected_label: str | None = None
    scrape_interval_minutes: int = DEFAULT_PRICE_INTERVAL_MINUTES
    # Optionaler Zielpreis; Alarm beim Unterschreiten.
    notify_threshold: float | None = None
    is_active: bool = True
    # Denormalisiert für schnelle Anzeige (zuletzt gemessener Preis).
    last_price: float | None = None
    initial_price: float | None = None
    last_checked_at: datetime | None = None
    # Letzter Extraktionsfehler (z.B. Locator gebrochen) für Transparenz im UI.
    last_error: str | None = None
    consecutive_failures: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    price_points: list["PricePoint"] = Relationship(
        back_populates="price_watch",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PricePoint(SQLModel, table=True):
    """Ein Preis-Datenpunkt; nur bei tatsächlicher Preisänderung gespeichert."""

    __tablename__ = "price_points"  # type: ignore
    __table_args__ = (Index("idx_price_points_watch_recorded", "pricewatch_id", "recorded_at"),)

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    pricewatch_id: int = Field(foreign_key="price_watches.id", ondelete="CASCADE", index=True)
    price: float
    currency: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)

    price_watch: "PriceWatch" = Relationship(back_populates="price_points")


# -------------------
# --- API-Schemas ---
# -------------------
class PriceCandidate(SQLModel):
    """Ein vom Backend vorgeschlagener Preis (für die Auswahl beim Anlegen)."""

    value: float
    currency: str | None = None
    label: str  # nutzerfreundliche Bezeichnung
    source: str  # "jsonld" | "meta" | "visible"
    locator: dict  # zur späteren Wiederfindung
    raw: str | None = None  # Originaltext der Preisangabe
    recommended: bool = False


class PriceWatchPreviewRequest(SQLModel):
    """Eingabe für den /preview-Endpoint: nur die zu prüfende URL."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)


class PriceWatchPreviewResponse(SQLModel):
    """Antwort des /preview-Endpoints: Seitentitel + gefundene Preis-Kandidaten."""

    title: str | None
    candidates: list[PriceCandidate]


class PriceWatchCreate(SQLModel):
    """API-Eingabe zum Anlegen eines Preis-Alarms (nach Auswahl der Preisangabe)."""

    name: str = ""
    url: str
    locator: dict
    currency: str | None = None
    selected_label: str | None = None
    scrape_interval_minutes: int = DEFAULT_PRICE_INTERVAL_MINUTES
    notify_threshold: float | None = None
    is_active: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_PRICE_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_PRICE_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class PriceWatchRead(SQLModel):
    """API-Ausgabe für einen Preis-Alarm."""

    id: int
    owner_id: str
    name: str
    url: str
    currency: str | None
    selected_label: str | None
    scrape_interval_minutes: int
    notify_threshold: float | None
    is_active: bool
    last_price: float | None
    initial_price: float | None
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime


class PriceWatchUpdate(SQLModel):
    """API-Eingabe für Teilaktualisierungen (Name, Intervall, Schwelle, Aktiv-Status)."""

    name: str | None = None
    scrape_interval_minutes: int | None = None
    notify_threshold: float | None = None
    is_active: bool | None = None

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v < MIN_PRICE_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_PRICE_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class PricePointRead(SQLModel):
    """API-Ausgabe für einen Preis-Datenpunkt (Verlaufsgraph)."""

    price: float
    currency: str | None
    recorded_at: datetime
