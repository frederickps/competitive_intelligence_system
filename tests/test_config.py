from cis.config.settings import Settings
import pytest


def test_sectors_parsed_correctly():
    settings = Settings(
        cis_domain="test_domain",
        cis_sectors="solar, Wind, HYDROGEN",
        postgres_user="test",
        postgres_password="test",
        postgres_db="test",
        postgres_url="postgresql+asyncpg://test:test@localhost/test",
        neo4j_password="test",
        minio_secret_key="testtest",
    )
    assert settings.sectors == ["solar", "wind", "hydrogen"]
