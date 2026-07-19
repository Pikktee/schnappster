"""Fundgrube-Modell: Dauerbeobachtung der Kleinanzeigen-„Zu verschenken"-Kategorie.

Anders als ein normaler Suchauftrag (der ein konkretes Produkt sucht) beobachtet eine
``GiftWatch`` die ganze Verschenken-Kategorie im Umkreis und bewertet Funde nach einem
**Interessensprofil** (die „eigenen Regeln") statt nach Preis-Delta. Fachlich trägt die
``GiftWatch`` alle Regeln; technisch erzeugt sie beim Speichern ein ``AdSearch``-Kind
(Gift-URL, ``gift_watch_id``-Rückverweis), damit die erprobte Scrape-/Analyse-Pipeline
unverändert weiterläuft — dasselbe Muster wie ``SearchOrder`` → ``AdSearch``.
"""

import re
from datetime import UTC, datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

DEFAULT_GIFT_INTERVAL_MINUTES = 15  # gute Verschenk-Angebote sind schnell weg
MIN_GIFT_INTERVAL_MINUTES = 5
DEFAULT_GIFT_RADIUS_KM = 10

# Transport-Kapazität des Nutzers (speist die Aufwand-Achse der Bewertung).
VEHICLES = ("bike", "small_car", "estate", "van")
DEFAULT_VEHICLE = "small_car"

_PLZ_PATTERN = re.compile(r"\d{5}")


def _validate_postal_code(value: str) -> str:
    """Stellt sicher, dass eine 5-stellige deutsche PLZ vorliegt (Distanzbasis)."""
    cleaned = (value or "").strip()
    if not _PLZ_PATTERN.fullmatch(cleaned):
        raise ValueError("Bitte eine gültige 5-stellige Postleitzahl angeben.")
    return cleaned


def _validate_vehicle(value: str) -> str:
    """Beschränkt das Fahrzeug auf die bekannten Transport-Stufen."""
    if value not in VEHICLES:
        raise ValueError(f"Fahrzeug muss eines von {VEHICLES} sein.")
    return value


# ------------------------
# --- Datenbanktabelle ---
# ------------------------
class GiftWatch(SQLModel, table=True):
    """Dauerbeobachtung der Verschenken-Kategorie mit eigenem Bewertungs-Regelwerk."""

    __tablename__ = "gift_watches"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    name: str

    # Geografie — Distanzbasis + Scrape-Umkreis (harte Grenze in der Such-URL).
    postal_code: str
    radius_km: int = DEFAULT_GIFT_RADIUS_KM

    # Interessensprofil = die „eigenen Regeln".
    interest_profile: str | None = None  # Freitext, Herzstück fürs LLM
    focus_keywords: str | None = None  # Schwerpunkte (Boost), komma-separiert
    exclude_keywords: str | None = None  # harter Text-Ausschluss
    exclude_categories: str | None = None  # harter Kategorie-Ausschluss (category_l2)

    # Transport-Profil → Aufwand-Achse.
    vehicle: str = DEFAULT_VEHICLE
    can_carry_heavy: bool = False

    # Bewertung.
    min_score_notify: float = Field(default=6.0, ge=0, le=10)

    is_active: bool = True
    scrape_interval_minutes: int = DEFAULT_GIFT_INTERVAL_MINUTES
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# -------------------
# --- API-Schemas ---
# -------------------
class GiftWatchCreate(SQLModel):
    """API-Eingabe zum Anlegen einer Fundgrube-Beobachtung."""

    name: str = ""
    postal_code: str
    radius_km: int = DEFAULT_GIFT_RADIUS_KM
    interest_profile: str | None = None
    focus_keywords: str | None = None
    exclude_keywords: str | None = None
    exclude_categories: str | None = None
    vehicle: str = DEFAULT_VEHICLE
    can_carry_heavy: bool = False
    min_score_notify: float = Field(default=6.0, ge=0, le=10)
    is_active: bool = True
    scrape_interval_minutes: int = DEFAULT_GIFT_INTERVAL_MINUTES

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        return _validate_postal_code(v)

    @field_validator("vehicle")
    @classmethod
    def validate_vehicle(cls, v: str) -> str:
        return _validate_vehicle(v)

    @field_validator("radius_km")
    @classmethod
    def validate_radius(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Der Radius muss größer als 0 km sein.")
        return v

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_GIFT_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_GIFT_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class GiftWatchUpdate(SQLModel):
    """API-Eingabe für Teilaktualisierungen (nur gesetzte Felder werden übernommen)."""

    name: str | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    interest_profile: str | None = None
    focus_keywords: str | None = None
    exclude_keywords: str | None = None
    exclude_categories: str | None = None
    vehicle: str | None = None
    can_carry_heavy: bool | None = None
    min_score_notify: float | None = Field(default=None, ge=0, le=10)
    is_active: bool | None = None
    scrape_interval_minutes: int | None = None

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str | None) -> str | None:
        return _validate_postal_code(v) if v is not None else None

    @field_validator("vehicle")
    @classmethod
    def validate_vehicle(cls, v: str | None) -> str | None:
        return _validate_vehicle(v) if v is not None else None

    @field_validator("radius_km")
    @classmethod
    def validate_radius(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Der Radius muss größer als 0 km sein.")
        return v

    @field_validator("scrape_interval_minutes")
    @classmethod
    def validate_interval(cls, v: int | None) -> int | None:
        if v is not None and v < MIN_GIFT_INTERVAL_MINUTES:
            raise ValueError(
                f"Das Prüf-Intervall muss mindestens {MIN_GIFT_INTERVAL_MINUTES} Minuten betragen."
            )
        return v


class GiftWatchRead(SQLModel):
    """API-Ausgabe für eine Fundgrube-Beobachtung inkl. abgeleiteter Kennzahlen."""

    id: int
    owner_id: str
    name: str
    postal_code: str
    radius_km: int
    interest_profile: str | None
    focus_keywords: str | None
    exclude_keywords: str | None
    exclude_categories: str | None
    vehicle: str
    can_carry_heavy: bool
    min_score_notify: float
    is_active: bool
    scrape_interval_minutes: int
    created_at: datetime
    # Abgeleitet aus dem gekoppelten AdSearch-Kind (vom Router befüllt).
    adsearch_id: int | None = None
    ad_count: int = 0
    last_scraped_at: datetime | None = None
