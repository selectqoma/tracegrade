from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres
    DATABASE_URL: str = "postgresql+asyncpg://tracegrade:tracegrade@localhost:5432/tracegrade"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DB: str = "tracegrade"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY_DEV_BYPASS: bool = False

    # Ingest
    INGEST_BATCH_SIZE: int = 1000
    INGEST_FLUSH_INTERVAL: float = 5.0

    # Features
    PII_REDACTION_ENABLED: bool = False


settings = Settings()
