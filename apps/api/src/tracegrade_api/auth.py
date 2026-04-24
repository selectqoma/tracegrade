import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .models import ApiKey

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_api_key_scheme = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


def hash_api_key(key: str) -> str:
    return _pwd_context.hash(key)


def verify_api_key(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


async def require_project(
    api_key: Annotated[str | None, Security(_api_key_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> uuid.UUID:
    if settings.API_KEY_DEV_BYPASS:
        # Return a deterministic dev project UUID for local development.
        return uuid.UUID("00000000-0000-0000-0000-000000000001")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    result = await db.execute(select(ApiKey))
    rows = result.scalars().all()

    for row in rows:
        if verify_api_key(api_key, row.key_hash):
            return row.project_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )
