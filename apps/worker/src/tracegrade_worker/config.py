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

    # LLM
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str | None = None

    # Model selection
    SYNTHESIS_MODEL: str = "claude-opus-4-7"
    JUDGE_MODEL: str = "claude-haiku-4-5-20251001"


settings = Settings()
