from sqlmodel import Field, SQLModel


# ----------------------
# --- Database Table ---
# ----------------------
class AppSettings(SQLModel, table=True):
    __tablename__ = "app_settings"  # type: ignore

    key: str = Field(primary_key=True)
    value: str


# -------------------
# --- API Schemas ---
# -------------------
class AppSettingsRead(SQLModel):
    key: str
    value: str


class AppSettingsUpdate(SQLModel):
    value: str
