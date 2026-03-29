from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration settings for the Competitive Intelligence System.

    Attributes:
        model_config (dict): Configuration for the Pydantic model, including
            environment file settings.

        llm_provider (str): The provider for the language model
            (default: "openai").
        llm_model (str): The specific language model to use
            (default: "gpt-4o").
        embedding_provider (str): The provider for the embedding model
            (default: "openai").
        embedding_model (str): The specific embedding model to use
            (default: "text-embedding-3-small").
        openai_api_key (str): The API key for OpenAI services.

        cis_domain (str): The domain for the competitive intelligence system.
        cis_sectors (str): A comma-separated string of sectors relevant to
            the domain.

        postgres_user (str): The username for the PostgreSQL database.
        postgres_password (str): The password for the PostgreSQL database.
        postgres_db (str): The name of the PostgreSQL database.
        postgres_url (str): The URL for connecting to the PostgreSQL database.

        qdrant_url (str): The URL for connecting to the Qdrant vector
            database (default: "http://localhost:6333").

        neo4j_uri (str): The URI for connecting to the Neo4j graph database
            (default: "bolt://localhost:7687").
        neo4j_user (str): The username for the Neo4j database
            (default: "neo4j").
        neo4j_password (str): The password for the Neo4j database.

        minio_endpoint (str): The MinIO endpoint
            (default: "localhost:9000").
        minio_access_key (str): The access key for MinIO
            (default: "minioadmin").
        minio_secret_key (str): The secret key for MinIO.
        minio_bucket (str): The bucket name for raw documents
            (default: "cis-raw-documents").

    Methods:
        sectors() -> list[str]: Returns the list of sectors from the
            comma-separated string.

    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM and embedding provider settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str = ""

    # Application settings
    cis_domain: str
    cis_sectors: str

    # PostgreSQL connection settings
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_url: str

    # Qdrant connection settings
    qdrant_url: str = "http://localhost:6333"

    # Neo4j connection settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # MinIO connection settings
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str
    minio_bucket: str = "cis-raw-documents"

    @property
    def sectors(self) -> list[str]:
        """Returns the list of sectors from the comma-separated string."""
        return [sector.strip().lower() for sector in self.cis_sectors.split(",")]


settings = Settings()
