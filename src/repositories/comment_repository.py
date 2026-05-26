from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.models.comment import Comment


class CommentRepository(ABC):
    @abstractmethod
    async def add_comment(self, comment: Comment) -> Comment:
        raise NotImplementedError

    @abstractmethod
    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        raise NotImplementedError

    @abstractmethod
    async def delete_comment(self, comment_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_comments_for_response(self, response_id: UUID) -> List[Comment]:
        raise NotImplementedError
