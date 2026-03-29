from pathlib import Path

import psycopg

from cis.config.settings import settings

CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def run_migrations() -> None:
    url = settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("localhost", "127.0.0.1") + "?gssencmode=disable"
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(CREATE_MIGRATIONS_TABLE)

        migrations_path = Path(__file__).parent
        migration_files = sorted(migrations_path.glob("*.sql"))

        for migration_file in migration_files:
            filename = migration_file.name
            row = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)
            ).fetchone()
            if not row:
                sql = migration_file.read_text(encoding="utf-8")
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,)
                )
                print(f"Applied migration: {filename}")
            else:
                print(f"Skipping already applied migration: {filename}")


if __name__ == "__main__":
    run_migrations()
