"""Error log database model and API schema."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Avoid linter error
    from app.models.adsearch import AdSearch


# ----------------------
# --- Database Table ---
# ----------------------
class ErrorLog(SQLModel, table=True):
    """Error log database table (scrape/AI errors for display in frontend)."""
    __tablename__ = "error_logs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id")
    error_type: str
    message: str
    details: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    adsearch: Optional["AdSearch"] = Relationship(back_populates="error_logs")


# -------------------
# --- API Schemas ---
# -------------------
class ErrorLogRead(SQLModel):
    """API output schema for an error log entry."""

    id: int
    adsearch_id: int | None
    error_type: str
    message: str
    details: str | None
    created_at: datetime
