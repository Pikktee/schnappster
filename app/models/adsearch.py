"""Ad search (Suchauftrag) model, validation, and API schemas."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import field_validator
from sqlmodel import Field, Relationship, SQLModel

_SEARCH_PREFIX = "https://www.kleinanzeigen.de/s-"
_DETAIL_PREFIX = "https://www.kleinanzeigen.de/s-anzeige/"


def _validate_search_url(url: str) -> str:
    """Ensure URL is a Kleinanzeigen.de search results page (not detail page or bare prefix)."""
    if not url.startswith(_SEARCH_PREFIX):
        raise ValueError(
            "Nur Kleinanzeigen.de-Suchergebnislisten sind erlaubt "
            "(URL muss mit https://www.kleinanzeigen.de/s- beginnen)."
        )
    if url.startswith(_DETAIL_PREFIX):
        raise ValueError(
            "Bitte keine Anzeigen-Detailseite eingeben — "
            "nur Suchergebnislisten sind erlaubt."
        )
    # Require something meaningful after "s-" (not just the bare prefix)
    remainder = url[len(_SEARCH_PREFIX):].strip("/")
    if not remainder:
        raise ValueError(
            "Bitte eine vollständige Suchergebnisliste-URL eingeben, nicht nur das Präfix."
        )
    return url

if TYPE_CHECKING:  # Avoid linter error
    from app.models.ad import Ad
    from app.models.errorlog import ErrorLog
    from app.models.scraperun import ScrapeRun


# ----------------------
# --- Database Table ---
# ----------------------
class AdSearch(SQLModel, table=True):
    """Ad search (Suchauftrag) database table."""

    __tablename__ = "ad_searches"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    url: str
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_scraped_at: datetime | None = None

    ads: list["Ad"] = Relationship(back_populates="adsearch")
    scrape_runs: list["ScrapeRun"] = Relationship(back_populates="adsearch")
    error_logs: list["ErrorLog"] = Relationship(back_populates="adsearch")


# -------------------
# --- API Schemas ---
# -------------------
class AdSearchCreate(SQLModel):
    """API input schema for creating an ad search."""

    name: str = ""
    url: str
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is a search results page."""
        return _validate_search_url(v)


class AdSearchRead(SQLModel):
    """API output schema for an ad search."""

    id: int
    name: str
    url: str
    prompt_addition: str | None
    min_price: float | None
    max_price: float | None
    blacklist_keywords: str | None
    is_exclude_images: bool
    is_active: bool
    scrape_interval_minutes: int
    created_at: datetime
    last_scraped_at: datetime | None


class AdSearchUpdate(SQLModel):
    """API input schema for partial updates to an ad search."""

    name: str | None = None
    url: str | None = None
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
        """Validate URL when provided."""
        if v is not None:
            _validate_search_url(v)
        return v
