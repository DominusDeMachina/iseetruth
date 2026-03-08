from app.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.postgres_user == "osint"
    assert s.postgres_db == "osint"
    assert s.api_port == 8000
    assert "http://localhost" in s.cors_origins
    assert s.redis_url == "redis://redis:6379/0"
    assert s.neo4j_uri == "bolt://neo4j:7687"
    assert s.qdrant_url == "http://qdrant:6333"
    assert s.ollama_base_url == "http://ollama:11434"


def test_cors_origins_from_comma_string():
    s = Settings(
        _env_file=None,
        cors_origins="http://localhost,http://example.com",
    )
    assert s.cors_origins == ["http://localhost", "http://example.com"]
