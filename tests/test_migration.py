from pathlib import Path

import psycopg
import pytest

from cis.config.settings import settings
from migrations.run_migrations import run_migrations


def _pg_url() -> str:
    url = settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("localhost", "127.0.0.1")
    return url + "?gssencmode=disable"


@pytest.fixture(autouse=True)
def clean_db():
    with psycopg.connect(_pg_url(), autocommit=True) as conn:
        conn.execute("""
            DROP TABLE IF EXISTS
                job_log, chunks, sources, sectors, domains, schema_migrations
            CASCADE
        """)


def test_tables_exist_after_migrations():
    run_migrations()

    with psycopg.connect(_pg_url()) as conn:
        for table in ["domains", "sectors", "sources", "chunks", "job_log"]:
            row = conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table,)
            ).fetchone()
            assert row, f"Table '{table}' was not created"


def test_migrations_idempotent():
    run_migrations()
    run_migrations()

    migrations_path = Path(__file__).parent.parent / "migrations"
    count_migration_files = len(list(migrations_path.glob("*.sql")))

    with psycopg.connect(_pg_url()) as conn:
        count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == count_migration_files  # no duplicates after second run
