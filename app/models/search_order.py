"""Suchauftrag-Eltern-Modell: EIN Suchbegriff über mehrere Quellen (Kleinanzeigen/eBay/MyDealz).

Der ``SearchOrder`` ist die Nutzer-Sicht auf einen Suchauftrag; die Quellen-Anbindungen bleiben
die erprobten Kinder ``AdSearch`` (Kleinanzeigen, eBay → KI-Analyse) und ``DealWatch`` (MyDealz →
Community-Temperatur). Anlegen/Bearbeiten läuft über den Eltern-Datensatz, die Scrape-/Check-
Pipelines arbeiten unverändert auf den Kindern.
"""

from datetime import UTC, datetime

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.models.adsearch import AdSearchRead
from app.models.deal_watch import DealWatchRead

DEFAULT_ORDER_INTERVAL_MINUTES = 60
MIN_ORDER_INTERVAL_MINUTES = 5


# ------------------------
# --- Datenbanktabelle ---
# ------------------------
class SearchOrder(SQLModel, table=True):
    """Eltern-Datensatz eines Suchauftrags; bündelt die Quellen-Kinder."""

    __tablename__ = "search_orders"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    name: str
    # Gemeinsamer Suchbegriff aller Quellen. Leer bei adoptierten URL-basierten Alt-Suchen.
    query: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# -------------------
# --- API-Schemas ---
# -------------------
class SearchOrderCreate(SQLModel):
    """Anlegen eines Suchauftrags: Suchbegriff + Quellen-Auswahl + Quellen-Einstellungen."""

    name: str = ""
    query: str
    scrape_interval_minutes: int = DEFAULT_ORDER_INTERVAL_MINUTES
    # Quellen-Auswahl (Checkboxen im Formular).
    use_kleinanzeigen: bool = True
    use_ebay: bool = False
    use_mydealz: bool = False
    # Gebraucht-Quellen (Kleinanzeigen & eBay teilen sich die Preisspanne).
    postal_code: str | None = None
    radius_km: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    prompt_addition: str | None = None
    is_exclude_images: bool = False
    # MyDealz (Neuware → eigene, meist höhere Preis-Obergrenze).
    mydealz_max_price: float | None = None
    mydealz_min_temperature: float | None = None
    mydealz_min_heating_velocity: float | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Bitte einen Suchbegriff angeben.")
        return v.strip()

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_ORDER_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_ORDER_INTERVAL_MINUTES} Minuten betragen."
            )
        return v

    @model_validator(mode="after")
    def _require_a_source(self) -> "SearchOrderCreate":
        if not (self.use_kleinanzeigen or self.use_ebay or self.use_mydealz):
            raise ValueError("Bitte mindestens eine Quelle auswählen.")
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("Der Radius muss größer als 0 km sein.")
        return self


class SearchOrderUpdate(SQLModel):
    """Teilaktualisierung: nur gesetzte Felder werden übernommen (exclude_unset)."""

    name: str | None = None
    query: str | None = None
    is_active: bool | None = None
    scrape_interval_minutes: int | None = None
    use_kleinanzeigen: bool | None = None
    use_ebay: bool | None = None
    use_mydealz: bool | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    prompt_addition: str | None = None
    is_exclude_images: bool | None = None
    mydealz_max_price: float | None = None
    mydealz_min_temperature: float | None = None
    mydealz_min_heating_velocity: float | None = None

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v < MIN_ORDER_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_ORDER_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class SearchOrderRead(SQLModel):
    """API-Ausgabe: Eltern-Felder + die Quellen-Kinder + abgeleitete Kennzahlen."""

    id: int
    owner_id: str
    name: str
    query: str
    is_active: bool
    created_at: datetime
    # Quellen-Kinder (None = Quelle nicht gewählt).
    kleinanzeigen: AdSearchRead | None = None
    ebay: AdSearchRead | None = None
    mydealz: DealWatchRead | None = None
    # Abgeleitet für Liste/Detail.
    ad_count: int = 0
    deal_count: int = 0
    last_checked_at: datetime | None = None
