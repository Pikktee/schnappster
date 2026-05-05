"""Datenbankmodell und API-Schema für KI-Analyse-Logs (nur erfolgreiche Analysen)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.ad import Ad
    from app.models.adsearch import AdSearch


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class AIAnalysisLog(SQLModel, table=True):
    """KI-Analyse-Log (eine Zeile pro erfolgreicher Analyse, Anzeige unter Logs > AI-Analysen)."""

    __tablename__ = "ai_analysis_logs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    ad_id: int | None = Field(default=None, foreign_key="ads.id", ondelete="SET NULL")
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id", ondelete="SET NULL")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_text: str = ""
    ad_title: str = ""
    score: float = Field(ge=0, le=10)
    ai_summary: str | None = None
    ai_reasoning: str | None = None
    estimated_market_price: float | None = None
    market_price_confidence: float | None = Field(default=None, ge=0, le=1)
    price_delta_percent: float | None = None
    comparison_count: int | None = None
    comparison_summary: str | None = None
    deal_evidence: dict[str, object] | None = Field(default=None, sa_column=Column(JSON))

    ad: "Ad" = Relationship(back_populates="ai_analysis_logs")
    adsearch: "AdSearch" = Relationship(back_populates="ai_analysis_logs")


# -------------------
# --- API-Schemas ---
# -------------------
class AIAnalysisLogRead(SQLModel):
    """API-Ausgabe-Schema für einen KI-Analyse-Log-Eintrag."""

    id: int
    ad_id: int | None
    adsearch_id: int | None
    created_at: datetime
    prompt_text: str
    ad_title: str
    score: float
    ai_summary: str | None
    ai_reasoning: str | None
    estimated_market_price: float | None
    market_price_confidence: float | None
    price_delta_percent: float | None
    comparison_count: int | None
    comparison_summary: str | None
    deal_evidence: dict[str, object] | None = Field(default=None, exclude=True)

    model_config = {"from_attributes": True}
