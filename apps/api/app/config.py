from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    postgres_user: str = "osint"
    postgres_password: str = "osint_dev"
    postgres_db: str = "osint"
    database_url: str = "postgresql://osint:osint_dev@postgres:5432/osint"

    # Neo4j
    neo4j_auth: str = "neo4j/osint_dev"
    neo4j_uri: str = "bolt://neo4j:7687"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_embedding_url: str = "http://ollama-embedding:11434"

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost", "http://localhost:5173"]

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # Auto-retry
    auto_retry_max_retries: int = 5
    auto_retry_base_delay_seconds: int = 30
    auto_retry_check_interval_seconds: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
