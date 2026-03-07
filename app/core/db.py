from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import config, get_app_root

(get_app_root() / "data").mkdir(exist_ok=True)
engine = create_engine(config.database_url, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_db_session():
    with Session(engine) as session:
        yield session


DbSession = Annotated[Session, Depends(get_db_session)]
