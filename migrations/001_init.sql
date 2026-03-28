-- Sources: tracks every ingested document
CREATE TABLE IF NOT EXISTS sources (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hash        VARCHAR(64) UNIQUE NOT NULL,  -- SHA-256 for deduplication
    domain      VARCHAR(128) NOT NULL,
    sector      VARCHAR(128) NOT NULL,
    source_type VARCHAR(32) NOT NULL,         -- pdf | html
    status      VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending | processing | done | error
    doc_date    DATE,
    chunk_count INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chunks: references to vectors stored in Qdrant
CREATE TABLE IF NOT EXISTS chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    qdrant_id   VARCHAR(64) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Job log: step-by-step pipeline audit trail
CREATE TABLE IF NOT EXISTS job_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    step        VARCHAR(64) NOT NULL,
    status      VARCHAR(32) NOT NULL,  -- started | done | error
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
