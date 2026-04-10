"""Datenbankmodell und API-Schema für Fehlerlogs."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Linter-Fehler vermeiden
    from app.models.adsearch import AdSearch


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class ErrorLog(SQLModel, table=True):
    """Fehlerlog-Tabelle (Scrape-/KI-Fehler für die Anzeige im Frontend)."""
    __tablename__ = "error_logs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id", ondelete="SET NULL")
    error_type: str
    message: str
    details: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    adsearch: Optional["AdSearch"] = Relationship(back_populates="error_logs")


# -------------------
# --- API-Schemas ---
# -------------------
class ErrorLogRead(SQLModel):
    """API-Ausgabe-Schema für einen Fehlerlog-Eintrag."""

    id: int
    adsearch_id: int | None
    error_type: str
    message: str
    details: str | None
    created_at: datetime
