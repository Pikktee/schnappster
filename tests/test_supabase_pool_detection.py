"""Reine URL-/Pool-Logik fuer Supabase (ohne echte DB-Verbindung)."""

from app.core.db import (
    cap_supabase_transaction_clients,
    database_url_psycopg_async,
    supabase_pooler_mode_from_url,
)


def test_pooler_shared_transaction_port() -> None:
    url = (
        "postgresql+psycopg://postgres.x:secret@"
        "aws-1-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert supabase_pooler_mode_from_url(url) == "transaction"


def test_pooler_shared_session_port() -> None:
    url = (
        "postgresql+psycopg://postgres.x:secret@"
        "aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
    )
    assert supabase_pooler_mode_from_url(url) == "session"


def test_pooler_shared_default_port_is_session() -> None:
    url = "postgresql+psycopg://u:p@aws-1-eu-central-1.pooler.supabase.com/postgres"
    assert supabase_pooler_mode_from_url(url) == "session"


def test_db_host_transaction_port() -> None:
    url = "postgresql+psycopg://postgres:pw@db.abcdefgh.supabase.co:6543/postgres"
    assert supabase_pooler_mode_from_url(url) == "transaction"


def test_db_host_direct_is_none() -> None:
    url = "postgresql+psycopg://postgres:pw@db.abcdefgh.supabase.co:5432/postgres"
    assert supabase_pooler_mode_from_url(url) == "none"


def test_localhost_none() -> None:
    assert supabase_pooler_mode_from_url("postgresql+psycopg://u:p@127.0.0.1:5432/db") == "none"


def test_cap_splits_pool_and_overflow_under_total() -> None:
    ps, mo = cap_supabase_transaction_clients(12, 12, 10)
    assert ps + mo == 10
    assert ps >= 1
    assert mo >= 1  # nicht nur pool_size=kappen (vermeidet max_overflow=0 bei Cap)


def test_cap_noop_when_under_limit() -> None:
    assert cap_supabase_transaction_clients(5, 5, 20) == (5, 5)


def test_database_url_psycopg_async_from_psycopg() -> None:
    u = "postgresql+psycopg://u:p@host:6543/db"
    assert database_url_psycopg_async(u) == "postgresql+psycopg_async://u:p@host:6543/db"


def test_database_url_psycopg_async_from_plain_postgresql() -> None:
    u = "postgresql://u:p@host:5432/db"
    assert database_url_psycopg_async(u) == "postgresql+psycopg_async://u:p@host:5432/db"
