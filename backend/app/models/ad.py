from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models.adsearch import AdSearch


class AdBase(SQLModel):
    external_id: str
    title: str
    description: str | None = None
    price: float | None = None
    location: str | None = None
    url: str
    image_urls: str | None = None


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
