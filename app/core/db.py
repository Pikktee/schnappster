"""Datenbank-Engine, Session-Abhaengigkeiten und Initialisierung."""

import logging
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import Depends
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine, text

from app.core.auth import CurrentUser, get_current_user
from app.core.config import config

logger = logging.getLogger(__name__)

# Wenn ``db_statement_timeout_ms`` in .env auf 0 steht, wuerden weder libpq-``options`` noch
# SET LOCAL greifen — einzelne Queries koennen dann unbegrenzt haengen (Browser/curl: 0 Bytes).
_API_STATEMENT_FALLBACK_MS = 25_000


def _api_statement_timeout_ms_effective() -> int:
    """Server-``statement_timeout`` (ms) fuer den API-Pool; bei Config 0 Fallback."""
    raw = config.db_statement_timeout_ms
    return int(_API_STATEMENT_FALLBACK_MS if raw <= 0 else raw)


# Gemeinsame libpq/psycopg-Optionen (API- und Background-Engine).
_base_connect_args: dict[str, object] = {
    "connect_timeout": config.db_connect_timeout,
    # prepare_threshold=None: psycopg3 darf keine server-seitigen prepared statements nutzen.
    # Supabase Transaction-Mode-Pooler (Supavisor) routet Queries an wechselnde Backends —
    # prepared statements sind dort nicht portabel und loesen DuplicatePreparedStatement aus.
    "prepare_threshold": None,
}

# Nur API-Pool: Postgres bricht einzelne Statements ab (ms). Sonst koennen Locks den
# Thread blockieren und der Browser sieht „pending“ ohne Ende.
_api_connect_args: dict[str, object] = dict(_base_connect_args)
_api_connect_args["options"] = (
    f"-c statement_timeout={_api_statement_timeout_ms_effective()}"
)

# libpq-TCP-Keepalive: tote/halboffene Verbindungen zum Transaction-Pooler schneller erkennen,
# statt bis zum HTTP-Timeout auf nie eintreffende Bytes zu warten.
_api_connect_args["keepalives"] = 1
_api_connect_args["keepalives_idle"] = 15
_api_connect_args["keepalives_interval"] = 5
_api_connect_args["keepalives_count"] = 4
# Halboffene TCPs zum Pooler schneller abbrechen (Millisekunden, libpq).
_api_connect_args["tcp_user_timeout"] = 20_000


def database_url_psycopg_async(database_url: str) -> str:
    """Wandelt die Sync-URL in die SQLAlchemy-/psycopg-Async-Variante um."""
    for sync_prefix, async_prefix in (
        ("postgresql+psycopg://", "postgresql+psycopg_async://"),
        ("postgresql://", "postgresql+psycopg_async://"),
    ):
        if database_url.startswith(sync_prefix):
            return async_prefix + database_url[len(sync_prefix) :]
    raise ValueError(
        "DATABASE_URL muss mit postgresql+psycopg:// oder postgresql:// beginnen "
        "(async API-Lesepfad)."
    )


# Supabase: Transaction-Mode typisch Port 6543 (Shared Pooler oder db.*.supabase.co).
# Session-Mode auf *.pooler.supabase.com:5432 — striktes Client-Limit
# (FATAL: MaxClientsInSessionMode).
_SUPABASE_POOLER_TRANSACTION_PORT = 6543


def supabase_pooler_mode_from_url(database_url: str) -> Literal["none", "transaction", "session"]:
    """Erkennt Supabase-Pool-Modus aus der URL (ohne Engine zu oeffnen)."""
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or 5432

    if host.endswith(".pooler.supabase.com"):
        if port == _SUPABASE_POOLER_TRANSACTION_PORT:
            return "transaction"
        return "session"

    # Dashboard-Preset „Transaction“: db.<ref>.supabase.co:6543 (ohne pooler-Hostname)
    if host.endswith(".supabase.co") and port == _SUPABASE_POOLER_TRANSACTION_PORT:
        return "transaction"

    return "none"


def cap_supabase_transaction_clients(
    pool_size: int, max_overflow: int, max_total: int
) -> tuple[int, int]:
    """Begrenzt pool_size + max_overflow auf max_total.

    Liegt die Summe ueber der Cap, wird bewusst **Overflow** genutzt (~40% der Cap),
    statt nur pool_size zu kappen: Sonst haette man oft ``max_overflow=0`` — bei
    kurzen parallelen Spitzen (Browser + curl + Scheduler) blockieren dann alle
    festen Slots und neue Requests warten bis ``pool_timeout``.
    """
    pool_size = max(pool_size, 1)
    max_overflow = max(max_overflow, 0)
    if pool_size + max_overflow <= max_total:
        return pool_size, max_overflow

    # Basis-Pool ~60% der Cap (mind. 1), Rest Overflow — Gesamtzahl Clients unveraendert begrenzt.
    base_target = max(1, (max_total * 3) // 5)
    base = min(pool_size, max(1, base_target))
    overflow_allow = max_total - base
    new_overflow = min(max_overflow, max(0, overflow_allow))
    new_pool = max(1, max_total - new_overflow)
    new_overflow = min(new_overflow, max_total - new_pool)
    return new_pool, new_overflow


_pooler_mode = supabase_pooler_mode_from_url(config.database_url)
_parsed_for_log = urlparse(config.database_url)
_log_host = _parsed_for_log.hostname or "?"
_log_port = _parsed_for_log.port or 5432


def log_database_pool_at_startup() -> None:
    """Nach ``setup_logging()`` aufrufen (z. B. im FastAPI-Lifespan).

    Beim Modulimport liegt der Root-Logger noch typischerweise auf WARNING —
    dann wuerden ``logger.info``/``warning`` aus dieser Datei untergehen.
    """
    if _pooler_mode == "session":
        logger.warning(
            "DATABASE_URL nutzt den Supabase Session-Pooler (typisch Port 5432). "
            "Bitte auf Transaction-Pooler wechseln (Port %s bzw. Dashboard-Preset "
            "„Transaction“), sonst droht MaxClientsInSessionMode / harte Parallelitaetsgrenzen.",
            _SUPABASE_POOLER_TRANSACTION_PORT,
        )
    logger.info(
        "DB API pool: supabase_mode=%s host=%s port=%s "
        "pool_size=%s max_overflow=%s (tx_cap_total=%s) statement_timeout_ms=%s pool_recycle=%s",
        _pooler_mode,
        _log_host,
        _log_port,
        _api_pool_size,
        _api_max_overflow,
        config.db_supabase_tx_pool_max_total if _pooler_mode == "transaction" else "-",
        _api_statement_timeout_ms_effective(),
        _api_pool_recycle,
    )
    if config.db_statement_timeout_ms <= 0:
        logger.warning(
            "DB_STATEMENT_TIMEOUT_MS is 0 or unset for API semantics — using fallback %sms on "
            "connections (see _api_statement_timeout_ms_effective).",
            _API_STATEMENT_FALLBACK_MS,
        )
    logger.info(
        "DB API /ads: Sync-Session ueber db_engine (QueuePool) + anyio.to_thread "
        "(kein separater NullPool-Connect zum Pooler)"
    )


# Session-Pooler: nur eine stabile Verbindung im App-Pool (kein Overflow).
# Transaction-Pooler: QueuePool, aber Summe aus pool_size+max_overflow begrenzen
# (Supabase „max pooler clients“ pro Compute-Tier).
# Direkte DB / kein Supabase-Tx-Pool: volle Konfiguration.
if _pooler_mode == "session":
    _api_pool_size = 1
    _api_max_overflow = 0
elif _pooler_mode == "transaction":
    _api_pool_size, _api_max_overflow = cap_supabase_transaction_clients(
        config.db_pool_size,
        config.db_max_overflow,
        config.db_supabase_tx_pool_max_total,
    )
else:
    _api_pool_size = config.db_pool_size
    _api_max_overflow = config.db_max_overflow

# Transaction-Pooler: kuerzeres Recycle, damit „haengende“ Server-Sessions seltener
# an gepoolten Clients kleben (ohne Schema-Aenderung).
_api_pool_recycle = (
    min(config.db_pool_recycle, 120) if _pooler_mode == "transaction" else config.db_pool_recycle
)

# --- API-Engine: QueuePool fuer schnelle, kurzlebige Requests ---
db_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_api_connect_args,
    pool_size=_api_pool_size,
    max_overflow=_api_max_overflow,
    pool_timeout=config.db_pool_timeout,
    pool_recycle=_api_pool_recycle,
    pool_pre_ping=True,
    pool_use_lifo=True,
)

# --- Async-Engine nur fuer ausgewaehlte Leserouten (/ads): NullPool ---
# Bei ``asyncio.wait_for``-Timeout wird die Coroutine abgebrochen; die AsyncSession
# schliesst die Verbindung. Sync-``to_thread`` + wait_for laesst den Worker dagegen
# weiterlaufen und haelt QueuePool-Slots bis zum Ende der blockierenden Query.
api_async_engine = create_async_engine(
    database_url_psycopg_async(config.database_url),
    echo=False,
    connect_args=_api_connect_args,
    poolclass=NullPool,
)
api_async_session_maker = async_sessionmaker(
    api_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def apply_api_statement_timeout_async(session: AsyncSession) -> None:
    """SET LOCAL pro Transaktion (Startup-``statement_timeout`` am Pooler oft unzuverlaessig)."""
    await session.execute(
        text(f"SET LOCAL statement_timeout = {_api_statement_timeout_ms_effective()}")
    )


def apply_api_statement_timeout_sync(session: Session) -> None:
    """SET LOCAL fuer Sync-Sessions (z. B. /ads ueber Threadpool + ``db_engine``-QueuePool)."""
    ms = _api_statement_timeout_ms_effective()
    session.execute(text(f"SET LOCAL statement_timeout = {ms}"))


# --- Background-Engine: NullPool fuer Scraper/Analyzer, die Sessions minutenlang halten ---
# Separate Engine, damit lang laufende Hintergrund-Jobs nie den API-Pool blockieren.
bg_engine = create_engine(
    config.database_url,
    echo=False,
    connect_args=_base_connect_args,
    poolclass=NullPool,
)


def init_db() -> None:
    """Alle Tabellen anlegen und initialen Commit ausführen."""
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        _drop_obsolete_user_settings_columns_postgres(session)
        session.commit()


# Aus dem Modell entfernt; alte DBs koennen NOT NULL-Spalten haben, die INSERTs ohne Wert brechen.
_OBSOLETE_USER_SETTINGS_COLUMNS: tuple[str, ...] = ("notify_email", "notify_mode")


def _drop_obsolete_user_settings_columns_postgres(session: Session) -> None:
    """Entfernt Legacy-Spalten, die nicht mehr im SQLModel stehen (NOT NULL blockierte INSERTs)."""
    for column_name in _OBSOLETE_USER_SETTINGS_COLUMNS:
        session.execute(text(f"ALTER TABLE user_settings DROP COLUMN IF EXISTS {column_name}"))


def get_db_session():
    """Liefert eine DB-Session."""
    with Session(db_engine) as session:
        yield session


def get_user_db_session(current_user: CurrentUser = Depends(get_current_user)):  # noqa: B008
    """DB-Session mit Auth-Guard — stellt sicher, dass nur authentifizierte User zugreifen.

    Alle Routen filtern bereits auf Anwendungsebene nach ``owner_id``; Postgres-RLS
    (``set_config``) ist daher nicht noetig und wuerde den Transaction-Mode-Pooler
    von Supabase blockieren (Session-State ist dort nicht portabel).
    """
    with Session(db_engine) as session:
        yield session


# Abhängigkeit für FastAPI
DbSession = Annotated[Session, Depends(get_db_session)]
UserDbSession = Annotated[Session, Depends(get_user_db_session)]
