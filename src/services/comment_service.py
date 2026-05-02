import logging
from uuid import UUID
from typing import List, Optional

from src.models.comment import Comment
from src.repositories.comment_repository import CommentRepository
from src.repositories.response_repository import ResponseRepository

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        response_repo: ResponseRepository,
    ) -> None:
        self._comment_repo = comment_repo
        self._response_repo = response_repo

    async def add_comment(self, response_id: UUID, comment: Comment) -> Optional[Comment]:
        """Добавляет комментарий к отклику.

        Возвращает None, если отклик не найден.
        Использует model_copy вместо прямой мутации атрибута Pydantic-объекта.
        """
        response = await self._response_repo.get_response(response_id)
        if not response:
            logger.warning(
                "Attempt to add comment to non-existent response %s", response_id
            )
            return None

        # Pydantic v2: не мутируем объект напрямую, создаём новую копию
        comment = comment.model_copy(update={"response_id": response_id})

        created = await self._comment_repo.add_comment(comment)
        logger.info("Comment %s added to response %s", created.id, response_id)
        return created

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        return await self._comment_repo.get_comment(comment_id)

    async def delete_comment(self, comment_id: UUID) -> bool:
        deleted = await self._comment_repo.delete_comment(comment_id)
        if deleted:
            logger.info("Comment %s deleted", comment_id)
        else:
            logger.warning("Comment %s not found for deletion", comment_id)
        return deleted

    async def get_response_comments(
        self, response_id: UUID
    ) -> Optional[List[Comment]]:
        """Возвращает список комментариев или None, если отклик не существует.

        Возврат None (а не пустого списка) позволяет вызывающей стороне
        различить два случая: «отклик не найден» vs «комментариев нет».
        Handler должен вернуть 404 при None.
        """
        response = await self._response_repo.get_response(response_id)
        if not response:
            logger.warning(
                "Attempt to get comments for non-existent response %s", response_id
            )
            return None

        return await self._comment_repo.get_comments_for_response(response_id)
