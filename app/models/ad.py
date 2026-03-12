"""Datenbankmodell und API-Lese-Schema für Anzeigen (Kleinanzeigen)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Linter-Fehler vermeiden
    from app.models.adsearch import AdSearch
    from app.models.logs_aianalysis import AIAnalysisLog


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class Ad(SQLModel, table=True):
    """Datenbanktabelle für Anzeigen (Kleinanzeigen)."""

    __tablename__ = "ads"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id", ondelete="SET NULL")
    external_id: str
    title: str
    description: str | None = None
    price: float | None = None
    postal_code: str | None = None
    city: str | None = None
    url: str
    image_urls: str | None = None
    condition: str | None = None
    shipping_cost: str | None = None
    seller_name: str | None = None
    seller_url: str | None = None
    seller_rating: int | None = None
    seller_is_friendly: bool = False
    seller_is_reliable: bool = False
    seller_type: str | None = None
    seller_active_since: str | None = None
    bargain_score: float | None = Field(default=None, ge=0, le=10)
    ai_summary: str | None = None
    ai_reasoning: str | None = None
    is_analyzed: bool = False
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    adsearch: "AdSearch" = Relationship(back_populates="ads")
    ai_analysis_logs: list["AIAnalysisLog"] = Relationship(back_populates="ad")


# -------------------
# --- API-Schemas ---
# -------------------
class AdRead(SQLModel):
    """Lese-Schema für Anzeigen in API-Antworten."""

    id: int
    adsearch_id: int | None
    external_id: str
    title: str
    description: str | None
    price: float | None
    postal_code: str | None
    city: str | None
    url: str
    image_urls: str | None = Field(default=None, exclude=True)
    condition: str | None
    shipping_cost: str | None
    seller_name: str | None
    seller_url: str | None
    seller_rating: int | None = None
    seller_is_friendly: bool
    seller_is_reliable: bool
    seller_type: str | None
    seller_active_since: str | None
    bargain_score: float | None
    ai_summary: str | None
    ai_reasoning: str | None
    is_analyzed: bool
    first_seen_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def image_url(self) -> str | None:
        """First image URL from comma-separated image_urls, or None if empty."""
        return self.image_urls.split(",")[0] if self.image_urls else None
