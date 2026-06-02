import logging
from uuid import UUID
from typing import List, Optional

from src.models.comment import Comment
from src.repositories.comment_repository import CommentRepository
from src.repositories.denorm_repository import DenormRepository
from src.services.kafka_producer import KafkaProducerService

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        denorm_repo: DenormRepository,
        kafka_producer: KafkaProducerService | None = None,
    ) -> None:
        self._comment_repo = comment_repo
        self._denorm_repo = denorm_repo
        self._kafka_producer = kafka_producer

    async def _attach_user_names(self, comments: List[Comment]) -> List[Comment]:
        if not comments:
            return comments
        user_ids = list({comment.user_id for comment in comments})
        names = await self._denorm_repo.get_user_names(user_ids)
        return [
            comment.model_copy(
                update={"user_name": names.get(comment.user_id, "") or ""}
            )
            for comment in comments
        ]

    async def add_comment(self, post_id: UUID, comment: Comment) -> Optional[Comment]:
        # Lazy-register post if Kafka post.created was missed (e.g. service was down).
        # post_id is validated by the caller navigating to a real post page.
        if not await self._denorm_repo.post_exists(post_id):
            logger.info("Post %s not in denorm, registering lazily", post_id)
            await self._denorm_repo.upsert_post(post_id, None)

        comment = comment.model_copy(update={"post_id": post_id})
        await self._denorm_repo.upsert_user(comment.user_id)

        created = await self._comment_repo.add_comment(comment)
        logger.info("Comment %s added to post %s", created.id, post_id)

        if self._kafka_producer is not None and created.id is not None:
            await self._kafka_producer.send_comment_created(
                str(created.id), str(post_id), str(comment.user_id)
            )

        enriched = await self._attach_user_names([created])
        return enriched[0]

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        comment = await self._comment_repo.get_comment(comment_id)
        if comment is None:
            return None
        enriched = await self._attach_user_names([comment])
        return enriched[0]

    async def delete_comment(self, comment_id: UUID) -> bool:
        comment = await self._comment_repo.get_comment(comment_id)
        if comment is None:
            logger.warning("Comment %s not found for deletion", comment_id)
            return False

        deleted = await self._comment_repo.delete_comment(comment_id)
        if not deleted:
            return False

        logger.info("Comment %s deleted", comment_id)
        if self._kafka_producer is not None:
            await self._kafka_producer.send_comment_deleted(
                str(comment_id), str(comment.post_id)
            )
        return True

    async def get_post_comments(self, post_id: UUID) -> List[Comment]:
        if not await self._denorm_repo.post_exists(post_id):
            logger.info("Post %s not in denorm, returning empty comments", post_id)
            return []

        comments = await self._comment_repo.get_comments_for_post(post_id)
        return await self._attach_user_names(comments)
