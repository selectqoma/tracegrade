from collections.abc import AsyncGenerator
from typing import Any

import clickhouse_connect
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# ---------------------------------------------------------------------------
# Postgres / SQLAlchemy
# ---------------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# ClickHouse
# ---------------------------------------------------------------------------

_clickhouse_client: clickhouse_connect.driver.Client | None = None


def get_clickhouse() -> clickhouse_connect.driver.Client:
    global _clickhouse_client
    if _clickhouse_client is None:
        _clickhouse_client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB,
        )
    return _clickhouse_client


async def init_clickhouse() -> None:
    """Verify ClickHouse connectivity on startup."""
    client = get_clickhouse()
    client.ping()


async def close_clickhouse() -> None:
    global _clickhouse_client
    if _clickhouse_client is not None:
        _clickhouse_client.close()
        _clickhouse_client = None


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def init_redis() -> None:
    r = await get_redis()
    await r.ping()


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
