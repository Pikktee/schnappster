"""Datenbankmodell und API-Schema für KI-Analyse-Logs (nur erfolgreiche Analysen)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
    ad_id: int = Field(foreign_key="ads.id")
    adsearch_id: int = Field(foreign_key="ad_searches.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_text: str = ""
    ad_title: str = ""
    score: float = Field(ge=0, le=10)
    ai_summary: str | None = None
    ai_reasoning: str | None = None

    ad: "Ad" = Relationship(back_populates="ai_analysis_logs")
    adsearch: "AdSearch" = Relationship(back_populates="ai_analysis_logs")


# -------------------
# --- API-Schemas ---
# -------------------
class AIAnalysisLogRead(SQLModel):
    """API-Ausgabe-Schema für einen KI-Analyse-Log-Eintrag."""

    id: int
    ad_id: int
    adsearch_id: int
    created_at: datetime
    prompt_text: str
    ad_title: str
    score: float
    ai_summary: str | None
    ai_reasoning: str | None

    model_config = {"from_attributes": True}
