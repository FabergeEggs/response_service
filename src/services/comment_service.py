from uuid import UUID
from typing import List, Optional
from src.models.comment import Comment
from src.repositories.comment_repository import CommentRepository
from src.repositories.response_repository import ResponseRepository

class CommentService:
    def __init__(self, comment_repo: CommentRepository, response_repo: ResponseRepository):
        self._comment_repo = comment_repo
        self._response_repo = response_repo

    async def add_comment(self, response_id: UUID, comment: Comment) -> Optional[Comment]:
        # Проверяем существование отклика
        response = await self._response_repo.get_response(response_id)
        if not response:
            return None
        comment.response_id = response_id
        return await self._comment_repo.add_comment(comment)

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        return await self._comment_repo.get_comment(comment_id)

    async def delete_comment(self, comment_id: UUID) -> bool:
        return await self._comment_repo.delete_comment(comment_id)

    async def get_response_comments(self, response_id: UUID) -> List[Comment]:
        # Можно сначала проверить существование отклика, но не обязательно
        return await self._comment_repo.get_comments_for_response(response_id)
