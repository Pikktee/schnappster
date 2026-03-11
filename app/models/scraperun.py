"""Scrape run database model and API schema."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Avoid linter error
    from app.models.adsearch import AdSearch


# ----------------------
# --- Database Table ---
# ----------------------
class ScrapeRun(SQLModel, table=True):
    """Scrape run database table (one record per scrape execution)."""
    __tablename__ = "scrape_runs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int = Field(foreign_key="ad_searches.id")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    ads_found: int = 0
    ads_new: int = 0
    status: str = "running"

    adsearch: "AdSearch" = Relationship(back_populates="scrape_runs")


# -------------------
# --- API Schemas ---
# -------------------
class ScrapeRunRead(SQLModel):
    """API output schema for a scrape run."""

    id: int
    adsearch_id: int
    started_at: datetime
    finished_at: datetime | None
    ads_found: int
    ads_new: int
    status: str
