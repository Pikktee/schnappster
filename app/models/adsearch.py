"""Suchauftrag-Modell, Validierung und API-Schemas."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import field_validator, model_validator
from sqlmodel import Field, Relationship, SQLModel

_SEARCH_PREFIX = "https://www.kleinanzeigen.de/s-"
_DETAIL_PREFIX = "https://www.kleinanzeigen.de/s-anzeige/"


def _validate_search_url(url: str) -> str:
    """Stellt sicher, dass die URL eine Kleinanzeigen.de-Suchergebnisseite ist."""
    if not url.startswith(_SEARCH_PREFIX):
        raise ValueError(
            "Nur Kleinanzeigen.de-Suchergebnislisten sind erlaubt "
            "(URL muss mit https://www.kleinanzeigen.de/s- beginnen)."
        )
    if url.startswith(_DETAIL_PREFIX):
        raise ValueError(
            "Bitte keine Anzeigen-Detailseite eingeben — nur Suchergebnislisten sind erlaubt."
        )
    # Nach "s-" muss etwas Sinnvolles kommen (nicht nur das Präfix)
    remainder = url[len(_SEARCH_PREFIX) :].strip("/")
    if not remainder:
        raise ValueError(
            "Bitte eine vollständige Suchergebnisliste-URL eingeben, nicht nur das Präfix."
        )
    return url


if TYPE_CHECKING:  # Linter-Fehler vermeiden
    from app.models.ad import Ad
    from app.models.logs_aianalysis import AIAnalysisLog
    from app.models.logs_error import ErrorLog
    from app.models.logs_scraperun import ScrapeRun


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class AdSearch(SQLModel, table=True):
    """Datenbanktabelle für Suchaufträge."""

    __tablename__ = "ad_searches"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    owner_id: str = Field(index=True)
    # Eltern-Suchauftrag (SearchOrder); None nur bei frisch angelegten Alt-/Extension-Suchen,
    # die beim nächsten Listen-Abruf adoptiert werden.
    search_order_id: int | None = Field(default=None, foreign_key="search_orders.id", index=True)
    # Fundgrube-Eltern (GiftWatch); gesetzt bei Verschenken-Beobachtungen, sonst None.
    gift_watch_id: int | None = Field(default=None, foreign_key="gift_watches.id", index=True)
    name: str
    # Quelle/Plattform des Suchauftrags (Registry-Name); Default hält Altbestand bei Kleinanzeigen.
    platform: str = Field(default="kleinanzeigen")
    # Effektive Such-URL (bei Keyword-Suchen aus den Feldern unten abgeleitet und gespeichert).
    url: str
    # Keyword-basierte Suche (optional, rückwärtskompatibel zur reinen URL-Eingabe).
    search_query: str | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    # Ausgeschlossene Kleinanzeigen-Kategorien (category_l2), komma-separiert; von der
    # Fundgrube gespiegelt, aber generisch für jede Suche nutzbar.
    blacklist_categories: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_scraped_at: datetime | None = None

    ads: list["Ad"] = Relationship(back_populates="adsearch")
    scrape_runs: list["ScrapeRun"] = Relationship(back_populates="adsearch")
    error_logs: list["ErrorLog"] = Relationship(back_populates="adsearch")
    ai_analysis_logs: list["AIAnalysisLog"] = Relationship(back_populates="adsearch")


# -------------------
# --- API-Schemas ---
# -------------------
class AdSearchCreate(SQLModel):
    """API-Eingabe-Schema zum Anlegen eines Suchauftrags.

    Entweder ``url`` (direkte Suchergebnis-URL) ODER ``search_query`` (+ optional PLZ/Radius)
    angeben – genau eines von beiden. Die effektive URL wird serverseitig abgeleitet.
    """

    name: str = ""
    platform: str = "kleinanzeigen"
    url: str | None = None
    search_query: str | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Prüft die URL auf Suchergebnisseite, falls angegeben."""
        if v is None:
            return v
        return _validate_search_url(v)

    @model_validator(mode="after")
    def _require_url_or_query(self) -> "AdSearchCreate":
        """Genau eines von URL oder Suchbegriff; Radius (falls gesetzt) muss positiv sein."""
        has_url = bool(self.url and self.url.strip())
        has_query = bool(self.search_query and self.search_query.strip())
        if has_url == has_query:
            raise ValueError(
                "Bitte entweder eine Such-URL oder einen Suchbegriff angeben (nicht beides)."
            )
        if self.radius_km is not None and self.radius_km <= 0:
            raise ValueError("Der Radius muss größer als 0 km sein.")
        return self


class AdSearchRead(SQLModel):
    """API-Ausgabe-Schema für einen Suchauftrag."""

    id: int
    owner_id: str
    search_order_id: int | None = None
    name: str
    platform: str
    url: str
    search_query: str | None
    postal_code: str | None
    radius_km: int | None
    prompt_addition: str | None
    min_price: float | None
    max_price: float | None
    blacklist_keywords: str | None
    is_exclude_images: bool
    is_active: bool
    scrape_interval_minutes: int
    created_at: datetime
    last_scraped_at: datetime | None
    # Nur vom Suchauftrags-Endpoint befüllt (Funde dieser Quelle); sonst None.
    ad_count: int | None = None


class AdSearchUpdate(SQLModel):
    """API-Eingabe-Schema für Teilaktualisierungen eines Suchauftrags."""

    name: str | None = None
    url: str | None = None
    search_query: str | None = None
    postal_code: str | None = None
    radius_km: int | None = None
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool | None = None
    is_active: bool | None = None
    scrape_interval_minutes: int | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Prüft die URL auf Suchergebnisseite, falls angegeben."""
        if v is None:
            return v
        return _validate_search_url(v)
