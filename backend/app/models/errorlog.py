from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models.adsearch import AdSearch


class ErrorLog(SQLModel, table=True):
    __tablename__ = "error_logs"

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id")
    error_type: str
    message: str
    details: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    adsearch: AdSearch | None = Relationship(back_populates="error_logs")


class ErrorLogRead(SQLModel):
    id: int
    adsearch_id: int | None
    error_type: str
    message: str
    details: str | None
    created_at: datetime
