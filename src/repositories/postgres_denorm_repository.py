from typing import Dict, List, Optional
from uuid import UUID

import asyncpg

from src.repositories.denorm_repository import DenormRepository


class PostgresDenormRepository(DenormRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_user(self, user_id: UUID, name: str = "") -> None:
        query = """
        INSERT INTO denormalized_user (id, name)
        VALUES ($1, $2)
        ON CONFLICT (id) DO NOTHING
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, user_id, name)

    async def upsert_task(
        self,
        task_id: UUID,
        project_id: Optional[UUID] = None,
        project_status: str = "ACTIVE",
    ) -> None:
        query = """
        INSERT INTO denormalized_task (id, project_id, project_status)
        VALUES ($1, $2, $3::project_status)
        ON CONFLICT (id) DO UPDATE
        SET project_id = COALESCE(EXCLUDED.project_id, denormalized_task.project_id),
            project_status = EXCLUDED.project_status,
            updated_at = CURRENT_TIMESTAMP
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, task_id, project_id, project_status.upper())

    async def upsert_post(
        self,
        post_id: UUID,
        project_id: Optional[UUID] = None,
        project_status: str = "ACTIVE",
    ) -> None:
        query = """
        INSERT INTO denormalized_post (id, project_id, project_status)
        VALUES ($1, $2, $3::project_status)
        ON CONFLICT (id) DO UPDATE
        SET project_id = COALESCE(EXCLUDED.project_id, denormalized_post.project_id),
            project_status = EXCLUDED.project_status,
            updated_at = CURRENT_TIMESTAMP
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, post_id, project_id, project_status.upper())

    async def update_user(self, user_id: UUID, name: Optional[str] = None) -> None:
        if name is None:
            return
        query = """
        UPDATE denormalized_user
        SET name = COALESCE($2, name)
        WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, user_id, name)

    async def get_user_names(self, user_ids: List[UUID]) -> Dict[UUID, str]:
        if not user_ids:
            return {}
        query = """
        SELECT id, name FROM denormalized_user WHERE id = ANY($1::uuid[])
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, user_ids)
        return {row["id"]: row["name"] for row in rows}

    async def update_task_status(self, task_id: UUID, project_status: str) -> None:
        query = """
        UPDATE denormalized_task
        SET project_status = $2::project_status,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, task_id, project_status.upper())

    async def delete_task(self, task_id: UUID) -> None:
        query = "DELETE FROM denormalized_task WHERE id = $1"
        async with self._pool.acquire() as conn:
            await conn.execute(query, task_id)
