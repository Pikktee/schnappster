from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Avoid linter error
    from app.models.adsearch import AdSearch


# ----------------------
# --- Database Table ---
# ----------------------
class Ad(SQLModel, table=True):
    """
    Ad (Kleinanzeige) database table.
    """

    __tablename__ = "ads"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int = Field(foreign_key="ad_searches.id")
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


# -------------------
# --- API Schemas ---
# -------------------
class AdRead(SQLModel):
    """
    Ad (Kleinanzeige) read api schema
    """

    id: int
    adsearch_id: int
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
        return self.image_urls.split(",")[0] if self.image_urls else None
