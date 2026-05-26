from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg

from src.models.response import Response, ResponseStatus
from src.repositories.response_repository import ResponseRepository


def _to_model(row: asyncpg.Record) -> Response:
    files = row["files"] or []
    attached_files = [UUID(file_id) if isinstance(file_id, str) else file_id for file_id in files]
    status_raw = row["status"]
    status = ResponseStatus(status_raw.lower()) if isinstance(status_raw, str) else status_raw
    return Response(
        id=row["id"],
        task_id=row["task_id"],
        user_id=row["user_id"],
        text=row["text"],
        status=status,
        attached_files=attached_files,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresResponseRepository(ResponseRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        query = """
        SELECT id, task_id, user_id, text, status::text AS status, files, created_at, updated_at
        FROM response
        WHERE task_id = $1
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, task_id)
        return [_to_model(row) for row in rows]

    async def get_response(self, response_id: UUID) -> Optional[Response]:
        query = """
        SELECT id, task_id, user_id, text, status::text AS status, files, created_at, updated_at
        FROM response
        WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, response_id)
        return _to_model(row) if row else None

    async def add_response(self, response: Response) -> Response:
        query = """
        INSERT INTO response (id, user_id, task_id, text, status, files, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5::response_status, $6::text[], $7, $8)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                response.id,
                response.user_id,
                response.task_id,
                response.text,
                response.status.value.upper(),
                [str(fid) for fid in response.attached_files],
                response.created_at,
                response.updated_at,
            )
        return response

    async def change_response(
        self, response_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Response]:
        current = await self.get_response(response_id)
        if not current:
            return None
        patched = current.model_copy(update={**update_data, "updated_at": datetime.now(UTC)})
        query = """
        UPDATE response
        SET text = $2, status = $3::response_status, files = $4::text[], updated_at = $5
        WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                response_id,
                patched.text,
                patched.status.value.upper(),
                [str(fid) for fid in patched.attached_files],
                patched.updated_at,
            )
        return patched

    async def delete_response(self, response_id: UUID) -> bool:
        query = "DELETE FROM response WHERE id = $1"
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, response_id)
        return result.endswith("1")

    async def change_response_status(
        self, response_id: UUID, status: ResponseStatus
    ) -> Optional[Response]:
        return await self.change_response(response_id, {"status": status})

    async def append_to_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        response = await self.get_response(response_id)
        if not response:
            return False
        files = list(response.attached_files)
        if file_id not in files:
            files.append(file_id)
        updated = await self.change_response(response_id, {"attached_files": files})
        return updated is not None

    async def remove_from_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        response = await self.get_response(response_id)
        if not response:
            return False
        files = [fid for fid in response.attached_files if fid != file_id]
        updated = await self.change_response(response_id, {"attached_files": files})
        return updated is not None

    async def delete_responses_by_task_id(self, task_id: UUID) -> int:
        query = "DELETE FROM response WHERE task_id = $1"
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, task_id)
        # asyncpg returns e.g. "DELETE 3"
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def cancel_pending_by_task_id(self, task_id: UUID) -> int:
        query = """
        UPDATE response
        SET status = 'CANCELLED'::response_status,
            updated_at = NOW()
        WHERE task_id = $1 AND status = 'PENDING'::response_status
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, task_id)
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0
