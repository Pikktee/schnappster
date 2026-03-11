"""Application settings database table and API schemas."""

from sqlmodel import Field, SQLModel


# ----------------------
# --- Database Table ---
# ----------------------
class AppSettings(SQLModel, table=True):
    """Key-value settings table (e.g. exclude_commercial_sellers, min_seller_rating)."""
    __tablename__ = "app_settings"  # type: ignore

    key: str = Field(primary_key=True)
    value: str


# -------------------
# --- API Schemas ---
# -------------------
class AppSettingsRead(SQLModel):
    """API output schema for a single setting."""
    key: str
    value: str


class AppSettingsUpdate(SQLModel):
    """API input schema for updating a setting value."""
    value: str
