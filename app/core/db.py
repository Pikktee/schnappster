from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.config import config, get_app_root

(get_app_root() / "data").mkdir(exist_ok=True)


connect_args = {}
engine = create_engine(config.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.commit()


def get_db_session():
    with Session(engine) as session:
        # SQLite requires foreign_keys=ON for CASCADE/SET NULL to work
        session.execute(text("PRAGMA foreign_keys=ON"))
        yield session


# Dependency for fastapi
DbSession = Annotated[Session, Depends(get_db_session)]
