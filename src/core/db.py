import asyncpg

from src.core.config import settings


async def create_pool() -> asyncpg.Pool:
    dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10)
