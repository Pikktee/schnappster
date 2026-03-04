from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ad import Ad
    from app.models.errorlog import ErrorLog
    from app.models.scraperun import ScrapeRun


class AdSearch(SQLModel, table=True):
    """Database table."""

    __tablename__ = "ad_searches"

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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_scraped_at: datetime | None = None

    ads: list["Ad"] = Relationship(back_populates="adsearch")
    scrape_runs: list["ScrapeRun"] = Relationship(back_populates="adsearch")
    error_logs: list["ErrorLog"] = Relationship(back_populates="adsearch")


class AdSearchCreate(SQLModel):
    """API input schema for creating."""

    name: str
    url: str
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30


class AdSearchRead(SQLModel):
    """API output schema."""

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
    """API input schema for partial updates."""

    name: str | None = None
    url: str | None = None
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool | None = None
    is_active: bool | None = None
    scrape_interval_minutes: int | None = None
