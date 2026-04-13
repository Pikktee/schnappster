"""Datenbankmodell und API-Schema für Scrape-Läufe."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # Linter-Fehler vermeiden
    from app.models.adsearch import AdSearch


# ----------------------
# --- Datenbanktabelle ---
# ----------------------
class ScrapeRun(SQLModel, table=True):
    """Datenbanktabelle für Scrape-Läufe (ein Datensatz pro Scrape-Durchlauf)."""

    __tablename__ = "scrape_runs"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    adsearch_id: int | None = Field(default=None, foreign_key="ad_searches.id", ondelete="SET NULL")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    ads_found: int = 0
    # Anzahl der Anzeigen, die durch Filter (Preis, VB, Blacklist, Verkäufer, Rating, etc.)
    # verworfen wurden. Hilft in den Logs, die Effektivität der Filter zu sehen.
    ads_filtered: int = 0
    ads_new: int = 0

    adsearch: "AdSearch" = Relationship(back_populates="scrape_runs")


# -------------------
# --- API-Schemas ---
# -------------------
class ScrapeRunRead(SQLModel):
    """API-Ausgabe-Schema für einen Scrape-Lauf."""

    model_config = {"from_attributes": True}

    id: int
    adsearch_id: int | None
    started_at: datetime
    finished_at: datetime | None
    ads_found: int
    ads_filtered: int
    ads_new: int
