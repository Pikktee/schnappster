from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

# for avoiding linter errors
if TYPE_CHECKING:
    from app.models.ad import Ad
    from app.models.errorlog import ErrorLog
    from app.models.scraperun import ScrapeRun


class AdSearchBase(SQLModel):
    name: str
    url: str
    prompt_addition: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    blacklist_keywords: str | None = None
    is_exclude_images: bool = False
    is_active: bool = True
    scrape_interval_minutes: int = 30


class AdSearch(AdSearchBase, table=True):
    __tablename__ = "ad_searches"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_scraped_at: datetime | None = None

    ads: list["Ad"] = Relationship(back_populates="adsearch")
    scrape_runs: list["ScrapeRun"] = Relationship(back_populates="adsearch")
    error_logs: list["ErrorLog"] = Relationship(back_populates="adsearch")


class AdSearchCreate(AdSearchBase):
    pass


class AdSearchRead(AdSearchBase):
    id: int
    created_at: datetime
    last_scraped_at: datetime | None
