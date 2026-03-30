import psycopg
import psycopg.rows
import pytest

from cis.config.settings import settings
from cis.storage.postgres_client import PostgresClient


def _pg_url() -> str:
    url = settings.postgres_url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("localhost", "127.0.0.1")
    return url + "?gssencmode=disable"


@pytest.fixture(autouse=True)
def clean_db():
    with psycopg.connect(_pg_url(), autocommit=True) as conn:
        conn.execute("TRUNCATE job_log, chunks, sources, sectors, domains CASCADE")


@pytest.fixture
def client() -> PostgresClient:
    return PostgresClient(settings.postgres_url)


# --- Domain ---


async def test_get_or_create_domain_creates(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    assert domain_id is not None
    assert len(domain_id) > 0


async def test_get_or_create_domain_idempotent(client):
    id_first = await client.get_or_create_domain("renewable_energy")
    id_second = await client.get_or_create_domain("renewable_energy")
    assert id_first == id_second


async def test_get_or_create_domain_normalizes(client):
    id_lower = await client.get_or_create_domain("renewable_energy")
    id_upper = await client.get_or_create_domain("RENEWABLE_ENERGY")
    assert id_lower == id_upper


# --- Sector ---


async def test_get_or_create_sector_creates(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    sector_id = await client.get_or_create_sector(domain_id, "solar")

    async with await psycopg.AsyncConnection.connect(
        _pg_url(), row_factory=psycopg.rows.dict_row, autocommit=True
    ) as conn:
        cur = await conn.execute(
            "SELECT * FROM sectors WHERE id = %s::uuid",
            (sector_id,),
        )
        row = await cur.fetchone()

    assert row is not None
    assert row["sector"] == "solar"
    assert str(row["domain_id"]) == domain_id


async def test_get_or_create_sector_idempotent(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    id_first = await client.get_or_create_sector(domain_id, "solar")
    id_second = await client.get_or_create_sector(domain_id, "solar")
    assert id_first == id_second


# --- Sources ---


async def test_create_source(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    source_id = await client.create_source(
        hash="abc123",
        domain_id=domain_id,
        sector="solar",
        source_type="pdf",
        doc_date=None,
    )
    result = await client.get_source_by_hash("abc123")
    assert result is not None
    assert str(result["id"]) == source_id


async def test_create_source_duplicate_raises(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    await client.create_source(
        hash="abc123",
        domain_id=domain_id,
        sector="solar",
        source_type="pdf",
        doc_date=None,
    )
    with pytest.raises(Exception):
        await client.create_source(
            hash="abc123",
            domain_id=domain_id,
            sector="solar",
            source_type="pdf",
            doc_date=None,
        )


async def test_update_source_status(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    source_id = await client.create_source(
        hash="abc123",
        domain_id=domain_id,
        sector="solar",
        source_type="pdf",
        doc_date=None,
    )
    await client.update_source_status(source_id, "processing")
    result = await client.get_source(source_id)
    assert result["status"] == "processing"


async def test_update_chunk_count(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    source_id = await client.create_source(
        hash="abc123",
        domain_id=domain_id,
        sector="solar",
        source_type="pdf",
        doc_date=None,
    )
    await client.update_chunk_count(source_id, 42)
    result = await client.get_source(source_id)
    assert result["chunk_count"] == 42


async def test_list_sources_filters_by_domain(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    other_domain_id = await client.get_or_create_domain("pharma")
    await client.create_source("hash1", domain_id, "solar", "pdf", None)
    await client.create_source("hash2", other_domain_id, "biotech", "pdf", None)
    results = await client.list_sources("renewable_energy")
    assert len(results) == 1
    assert str(results[0]["domain_id"]) == domain_id


# --- Chunks ---


async def test_create_chunk(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    source_id = await client.create_source("hash1", domain_id, "solar", "pdf", None)
    chunk_id = await client.create_chunk(source_id, 0, "qdrant-abc")
    assert chunk_id is not None


# --- Job Log ---


async def test_log_job_multiple_steps(client):
    domain_id = await client.get_or_create_domain("renewable_energy")
    source_id = await client.create_source("hash1", domain_id, "solar", "pdf", None)
    await client.log_job(source_id, "normalize", "done")
    await client.log_job(source_id, "chunk", "done", detail="42 chunks")
    await client.log_job(source_id, "embed", "error", detail="timeout")

    async with await psycopg.AsyncConnection.connect(
        _pg_url(), row_factory=psycopg.rows.dict_row, autocommit=True
    ) as conn:
        cur = await conn.execute(
            "SELECT * FROM job_log WHERE source_id = %s::uuid ORDER BY created_at",
            (source_id,),
        )
        rows = await cur.fetchall()

    assert len(rows) == 3
    assert rows[0]["step"] == "normalize"
    assert rows[1]["detail"] == "42 chunks"
    assert rows[2]["status"] == "error"
