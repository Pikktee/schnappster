from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models.adsearch import AdSearch


class AdBase(SQLModel):
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
    seller_rating: str | None = None
    seller_is_friendly: bool = False
    seller_is_reliable: bool = False
    seller_type: str | None = None
    seller_active_since: str | None = None


class Ad(AdBase, table=True):
    __tablename__ = "ads"

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int = Field(foreign_key="ad_searches.id")
    bargain_score: float | None = Field(default=None, ge=0, le=10)
    ai_summary: str | None = None
    ai_reasoning: str | None = None
    is_analyzed: bool = False
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)

    adsearch: AdSearch = Relationship(back_populates="ads")


class AdRead(AdBase):
    id: int
    adsearch_id: int
    bargain_score: float | None
    ai_summary: str | None
    ai_reasoning: str | None
    is_analyzed: bool
    first_seen_at: datetime
