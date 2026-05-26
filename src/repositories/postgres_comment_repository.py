from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID, uuid4

import asyncpg

from src.models.comment import Comment
from src.repositories.comment_repository import CommentRepository


def _utc_naive(dt: datetime | None = None) -> datetime:
    value = dt or datetime.now(UTC)
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _to_model(row: asyncpg.Record) -> Comment:
    return Comment(
        id=row["id"],
        post_id=row["post_id"],
        user_id=row["user_id"],
        content=row["text"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresCommentRepository(CommentRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add_comment(self, comment: Comment) -> Comment:
        comment_id = comment.id or uuid4()
        created_at = _utc_naive(comment.created_at)
        updated_at = _utc_naive(comment.updated_at)
        query = """
        INSERT INTO comments (id, user_id, post_id, text, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                comment_id,
                comment.user_id,
                comment.post_id,
                comment.content,
                created_at,
                updated_at,
            )
        return comment.model_copy(update={"id": comment_id})

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        query = """
        SELECT id, user_id, post_id, text, created_at, updated_at
        FROM comments
        WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, comment_id)
        return _to_model(row) if row else None

    async def delete_comment(self, comment_id: UUID) -> bool:
        query = "DELETE FROM comments WHERE id = $1"
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, comment_id)
        return result.endswith("1")

    async def get_comments_for_post(self, post_id: UUID) -> List[Comment]:
        query = """
        SELECT id, user_id, post_id, text, created_at, updated_at
        FROM comments
        WHERE post_id = $1
        ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, post_id)
        return [_to_model(row) for row in rows]
