# Competitive Intelligence System (CIS)

Agentic system for market and competitive analysis.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Git

---

## Setup

**1. Clone the repository**
```bash
git clone <repo-url>
cd competetive_intelligence_system
```

**2. Create your environment file**
```bash
cp .env.example .env
```

Open `.env` and fill in all required values:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `NEO4J_PASSWORD`
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` (min. 8 characters)
- `OPENAI_API_KEY`

**3. Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash / Mac / Linux
```

---

## Start Services

Start all infrastructure services:
```bash
docker compose up postgres qdrant neo4j minio
```

Start a single service:
```bash
docker compose up postgres
```

Run in background (detached):
```bash
docker compose up postgres qdrant neo4j minio -d
```

---

## Stop Services

```bash
docker compose down
```

To also remove all volumes (wipes all data):
```bash
docker compose down -v
```

---

## Service URLs

| Service | URL |
|---|---|
| Qdrant Dashboard | http://localhost:6333/dashboard |
| Neo4j Browser | http://localhost:7474 |
| MinIO Console | http://localhost:9001 |
| API | http://localhost:8000 |
