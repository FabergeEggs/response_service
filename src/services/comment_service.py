import logging
from uuid import UUID
from typing import List, Optional

from src.models.comment import Comment
from src.repositories.comment_repository import CommentRepository
from src.repositories.denorm_repository import DenormRepository
from src.repositories.response_repository import ResponseRepository

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        response_repo: ResponseRepository,
        denorm_repo: DenormRepository | None = None,
    ) -> None:
        self._comment_repo = comment_repo
        self._response_repo = response_repo
        self._denorm_repo = denorm_repo

    async def _attach_user_names(self, comments: List[Comment]) -> List[Comment]:
        if not comments or self._denorm_repo is None:
            return comments
        user_ids = list({comment.user_id for comment in comments})
        names = await self._denorm_repo.get_user_names(user_ids)
        return [
            comment.model_copy(
                update={"user_name": names.get(comment.user_id, "") or ""}
            )
            for comment in comments
        ]

    async def add_comment(self, response_id: UUID, comment: Comment) -> Optional[Comment]:
        response = await self._response_repo.get_response(response_id)
        if not response:
            logger.warning(
                "Attempt to add comment to non-existent response %s", response_id
            )
            return None

        comment = comment.model_copy(update={"response_id": response_id})
        if self._denorm_repo is not None:
            await self._denorm_repo.upsert_user(comment.user_id)

        created = await self._comment_repo.add_comment(comment)
        logger.info("Comment %s added to response %s", created.id, response_id)
        enriched = await self._attach_user_names([created])
        return enriched[0]

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        comment = await self._comment_repo.get_comment(comment_id)
        if comment is None:
            return None
        enriched = await self._attach_user_names([comment])
        return enriched[0]

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
        response = await self._response_repo.get_response(response_id)
        if not response:
            logger.warning(
                "Attempt to get comments for non-existent response %s", response_id
            )
            return None

        comments = await self._comment_repo.get_comments_for_response(response_id)
        return await self._attach_user_names(comments)
