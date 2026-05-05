"""Datenbank-Engine, Session-Abhaengigkeiten und Initialisierung."""

import json
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config

_connect_args: dict[str, object] = {"connect_timeout": config.db_connect_timeout}
if config.db_statement_timeout_ms > 0:
    _connect_args["options"] = f"-c statement_timeout={config.db_statement_timeout_ms}"
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_connect_args,
    pool_size=config.db_pool_size,
    max_overflow=config.db_max_overflow,
    pool_timeout=config.db_pool_timeout,
    pool_pre_ping=True,
    pool_use_lifo=True,
)


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        _drop_obsolete_user_settings_columns_postgres(session)
        _ensure_ai_deal_columns_postgres(session)
        _ensure_query_indexes_postgres(session)
        session.commit()


# Aus dem Modell entfernt; alte DBs koennen NOT NULL-Spalten haben, die INSERTs ohne Wert brechen.
_OBSOLETE_USER_SETTINGS_COLUMNS: tuple[str, ...] = ("notify_email", "notify_mode")


def _drop_obsolete_user_settings_columns_postgres(session: Session) -> None:
    """Entfernt Legacy-Spalten, die nicht mehr im SQLModel stehen (NOT NULL blockierte INSERTs)."""
    for column_name in _OBSOLETE_USER_SETTINGS_COLUMNS:
        session.execute(text(f"ALTER TABLE user_settings DROP COLUMN IF EXISTS {column_name}"))


_AI_DEAL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("estimated_market_price", "DOUBLE PRECISION"),
    ("market_price_confidence", "DOUBLE PRECISION"),
    ("price_delta_percent", "DOUBLE PRECISION"),
    ("comparison_count", "INTEGER"),
    ("comparison_summary", "TEXT"),
    ("deal_evidence", "JSONB"),
)


def _ensure_ai_deal_columns_postgres(session: Session) -> None:
    """Adds evidence-based analysis columns to existing databases."""
    for table_name in ("ads", "ai_analysis_logs"):
        for column_name, column_type in _AI_DEAL_COLUMNS:
            statement = (
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
            )
            session.execute(text(statement))


def _ensure_query_indexes_postgres(session: Session) -> None:
    """Legt Indexe für die häufigsten Dashboard-Queries auch in bestehenden DBs an."""
    statements = (
        """
        CREATE INDEX IF NOT EXISTS idx_ads_first_seen_at
        ON ads(first_seen_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ads_adsearch_price
        ON ads(adsearch_id, price)
        WHERE price IS NOT NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_scrape_runs_adsearch_id
        ON scrape_runs(adsearch_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_scrape_runs_started_at
        ON scrape_runs(started_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_error_logs_adsearch_id
        ON error_logs(adsearch_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_error_logs_created_at
        ON error_logs(created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_adsearch_id
        ON ai_analysis_logs(adsearch_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_ad_id
        ON ai_analysis_logs(ad_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_created_at
        ON ai_analysis_logs(created_at DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ads_owner_analyzed_seen
        ON ads(owner_id, is_analyzed, first_seen_at DESC, id DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ads_owner_search_analyzed_seen
        ON ads(owner_id, adsearch_id, is_analyzed, first_seen_at DESC, id DESC)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_ads_owner_analyzed_score_seen
        ON ads(owner_id, is_analyzed, bargain_score DESC, first_seen_at DESC, id DESC)
        """,
    )
    for statement in statements:
        session.execute(text(statement))


def get_db_session():
    """Liefert eine DB-Session."""
    with Session(db_engine) as session:
        yield session


def set_user_db_claims(session: Session, current_user: CurrentUser) -> None:
    """Setzt JWT-Claims für die aktuelle DB-Verbindung.

    Session-weite Claims ueberstehen Commit/Rollback innerhalb einer Route; die Dependency
    setzt sie vor Rueckgabe der Pool-Verbindung wieder auf ein leeres JSON-Objekt.
    """
    claims = json.dumps(
        {
            "sub": current_user.user_id,
            "role": "authenticated",
            "app_metadata": current_user.app_metadata,
        },
        default=str,
        allow_nan=False,
    )
    session.execute(
        text("SELECT set_config('request.jwt.claims', :claims, false)"),
        {"claims": claims},
    )


def clear_user_db_claims(session: Session) -> None:
    """Entfernt User-Claims, bevor eine Verbindung in den Pool zurückgeht."""
    session.execute(text("SELECT set_config('request.jwt.claims', '{}', false)"))
    session.commit()


def get_user_db_session(current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """DB-Session im User-Kontext (JWT-Claims fuer Postgres-Sessions / RLS)."""
    with Session(db_engine) as session:
        # JWT-`sub` fuer RLS; kein set_config('role') (entspricht SET ROLE, oft fehlerhaft).
        set_user_db_claims(session, current_user)
        try:
            yield session
        finally:
            session.rollback()
            clear_user_db_claims(session)


# Abhängigkeit für FastAPI
DbSession = Annotated[Session, Depends(get_db_session)]
UserDbSession = Annotated[Session, Depends(get_user_db_session)]
