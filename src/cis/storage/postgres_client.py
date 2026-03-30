from __future__ import annotations

import logging
from datetime import date

import psycopg
import psycopg.rows

from cis.config.settings import settings

logger = logging.getLogger(__name__)


class PostgresClient:
    """Async PostgreSQL client for all CIS database operations.

    Wraps psycopg AsyncConnection. Each method opens and closes its own
    connection — no shared pool lifecycle required.
    """

    def __init__(self, url: str) -> None:
        """Initialise the client with a PostgreSQL connection URL.

        Normalises the URL from SQLAlchemy format to psycopg format and
        applies Windows/Docker compatibility fixes.

        Args:
            url: PostgreSQL connection URL (postgresql+asyncpg:// format from settings).
        """
        self._url = (
            url.replace("postgresql+asyncpg://", "postgresql://").replace("localhost", "127.0.0.1")
            + "?gssencmode=disable"
        )

    def _connect(self):
        """Return an async connection context manager with dict row factory.

        Uses autocommit=True so each statement is committed immediately without
        requiring explicit transaction management.
        """
        return psycopg.AsyncConnection.connect(
            self._url,
            row_factory=psycopg.rows.dict_row,
            autocommit=True,
        )

    async def get_or_create_domain(self, domain: str) -> str:
        """Return the UUID of a domain, creating it if it does not exist.

        Uses an atomic INSERT ... ON CONFLICT DO UPDATE ... RETURNING to avoid
        race conditions and retrieve the id in a single query.

        Args:
            domain: Domain name (e.g. "renewable_energy"). Normalised before storage.

        Returns:
            UUID of the domain as a string.
        """
        domain = domain.strip().lower()
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO domains (domain)
                VALUES (%s)
                ON CONFLICT (domain) DO UPDATE SET domain = EXCLUDED.domain
                RETURNING id
                """,
                (domain,),
            )

            row = await cur.fetchone()
            logger.debug("Domain resolved: %s -> %s", domain, row["id"])
            return str(row["id"])

    async def get_or_create_sector(self, domain_id: str, sector: str) -> str:
        """Return the UUID of a sector within a domain, creating it if it does not exist.

        Args:
            domain_id: UUID of the parent domain.
            sector: Sector name (e.g. "solar"). Normalised before storage.

        Returns:
            UUID of the sector as a string.
        """
        sector = sector.strip().lower()
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO sectors (domain_id, sector)
                VALUES (%s::uuid, %s)
                ON CONFLICT (domain_id, sector) DO UPDATE SET sector = EXCLUDED.sector
                RETURNING id
                """,
                (domain_id, sector),
            )
            row = await cur.fetchone()
            logger.debug("Sector resolved: %s → %s", sector, row["id"])
            return str(row["id"])

    async def create_source(
        self,
        hash: str,
        domain_id: str,
        sector: str,
        source_type: str,
        doc_date: date | None,
    ) -> str:
        """Insert a new source document record and return its UUID.

        Raises a database error on duplicate hash — callers should check via
        get_source_by_hash() first for deduplication.

        Args:
            hash: SHA-256 hash of the raw document content.
            domain_id: UUID of the domain this source belongs to.
            sector: Sector tag (e.g. "solar").
            source_type: Document type — "pdf" or "html".
            doc_date: Publication date of the document, or None if unknown.

        Returns:
            UUID of the created source as a string.
        """
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO sources (hash, domain_id, sector, source_type, doc_date)
                VALUES (%s, %s::uuid, %s, %s, %s)
                RETURNING id
                """,
                (hash, domain_id, sector, source_type, doc_date),
            )
            row = await cur.fetchone()
            logger.info("Source created: id=%s hash=%s", row["id"], hash)
            return str(row["id"])

    async def get_source_by_hash(self, hash: str) -> dict | None:
        """Look up a source by its SHA-256 hash for deduplication.

        Args:
            hash: SHA-256 hash of the document content.

        Returns:
            Source record as a dict, or None if not found.
        """
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM sources WHERE hash = %s",
                (hash,),
            )
            return await cur.fetchone()

    async def get_source(self, source_id: str) -> dict | None:
        """Fetch a source record by its UUID.

        Returns all columns including status and chunk_count.

        Args:
            source_id: UUID of the source.

        Returns:
            Source record as a dict, or None if not found.
        """
        async with await self._connect() as conn:
            cur = await conn.execute(
                "SELECT * FROM sources WHERE id = %s::uuid",
                (source_id,),
            )
            return await cur.fetchone()

    async def list_sources(self, domain: str) -> list[dict]:
        """Return all sources for a given domain, ordered by creation date descending.

        Args:
            domain: Domain name (e.g. "renewable_energy").

        Returns:
            List of source records as dicts.
        """
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                SELECT s.* FROM sources s
                JOIN domains d ON s.domain_id = d.id
                WHERE d.domain = %s
                ORDER BY s.created_at DESC
                """,
                (domain.strip().lower(),),
            )
            return await cur.fetchall()

    async def update_source_status(self, source_id: str, status: str) -> None:
        """Update the processing status of a source and refresh updated_at.

        Args:
            source_id: UUID of the source.
            status: New status — "pending", "processing", "done", or "error".
        """
        async with await self._connect() as conn:
            await conn.execute(
                """
                UPDATE sources
                SET status = %s, updated_at = NOW()
                WHERE id = %s::uuid
                """,
                (status, source_id),
            )
            logger.info("Source %s status → %s", source_id, status)

    async def update_chunk_count(self, source_id: str, count: int) -> None:
        """Set the chunk_count on a source after chunking is complete.

        Args:
            source_id: UUID of the source.
            count: Total number of chunks produced.
        """
        async with await self._connect() as conn:
            await conn.execute(
                """
                UPDATE sources
                SET chunk_count = %s, updated_at = NOW()
                WHERE id = %s::uuid
                """,
                (count, source_id),
            )
            logger.debug("Source %s chunk_count → %d", source_id, count)

    async def create_chunk(self, source_id: str, chunk_index: int, qdrant_id: str) -> str:
        """Insert a chunk reference linking a source to its Qdrant vector.

        Args:
            source_id: UUID of the parent source.
            chunk_index: Zero-based position of this chunk within the source.
            qdrant_id: ID of the corresponding vector in Qdrant.

        Returns:
            UUID of the created chunk record as a string.
        """
        async with await self._connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO chunks (source_id, chunk_index, qdrant_id)
                VALUES (%s::uuid, %s, %s)
                RETURNING id
                """,
                (source_id, chunk_index, qdrant_id),
            )
            row = await cur.fetchone()
            logger.debug(
                "Chunk created: source=%s index=%d qdrant_id=%s", source_id, chunk_index, qdrant_id
            )
            return str(row["id"])

    async def log_job(
        self,
        source_id: str,
        step: str,
        status: str,
        detail: str | None = None,
    ) -> None:
        """Append a pipeline audit entry to job_log.

        Args:
            source_id: UUID of the source being processed.
            step: Pipeline step name (e.g. "normalize", "chunk", "embed").
            status: Step outcome — "started", "done", or "error".
            detail: Optional message, e.g. chunk count or error description.
        """
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO job_log (source_id, step, status, detail)
                VALUES (%s::uuid, %s, %s, %s)
                """,
                (source_id, step, status, detail),
            )
            logger.debug("Job step logged: source=%s step=%s status=%s", source_id, step, status)


postgres_client = PostgresClient(settings.postgres_url)
