from sqlmodel import Field, SQLModel


class AppSettings(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str


class AppSettingsRead(SQLModel):
    key: str
    value: str


class AppSettingsUpdate(SQLModel):
    value: str
