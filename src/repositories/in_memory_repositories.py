from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.models.comment import Comment
from src.models.response import Response, ResponseStatus
from src.repositories.comment_repository import CommentRepository
from src.repositories.response_repository import ResponseRepository


class InMemoryResponseRepository(ResponseRepository):
    def __init__(self) -> None:
        self._responses: Dict[UUID, Response] = {}

    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        return [r for r in self._responses.values() if r.task_id == task_id]

    async def get_response(self, response_id: UUID) -> Optional[Response]:
        return self._responses.get(response_id)

    async def add_response(self, response: Response) -> Response:
        self._responses[response.id] = response
        return response

    async def change_response(
        self, response_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Response]:
        current = self._responses.get(response_id)
        if not current:
            return None
        updated = current.model_copy(update={**update_data, "updated_at": datetime.now(UTC)})
        self._responses[response_id] = updated
        return updated

    async def delete_response(self, response_id: UUID) -> bool:
        return self._responses.pop(response_id, None) is not None

    async def change_response_status(
        self, response_id: UUID, status: ResponseStatus
    ) -> Optional[Response]:
        return await self.change_response(response_id, {"status": status})

    async def append_to_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        response = self._responses.get(response_id)
        if not response:
            return False
        files = list(response.attached_files)
        if file_id not in files:
            files.append(file_id)
        updated = response.model_copy(
            update={"attached_files": files, "updated_at": datetime.now(UTC)}
        )
        self._responses[response_id] = updated
        return True

    async def remove_from_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        response = self._responses.get(response_id)
        if not response:
            return False
        files = [fid for fid in response.attached_files if fid != file_id]
        updated = response.model_copy(
            update={"attached_files": files, "updated_at": datetime.now(UTC)}
        )
        self._responses[response_id] = updated
        return True

    async def delete_responses_by_task_id(self, task_id: UUID) -> int:
        to_delete = [rid for rid, r in self._responses.items() if r.task_id == task_id]
        for rid in to_delete:
            del self._responses[rid]
        return len(to_delete)

    async def cancel_pending_by_task_id(self, task_id: UUID) -> int:
        count = 0
        for rid, response in list(self._responses.items()):
            if response.task_id == task_id and response.status == ResponseStatus.PENDING:
                self._responses[rid] = response.model_copy(
                    update={
                        "status": ResponseStatus.CANCELLED,
                        "updated_at": datetime.now(UTC),
                    }
                )
                count += 1
        return count


class InMemoryCommentRepository(CommentRepository):
    def __init__(self) -> None:
        self._comments: Dict[UUID, Comment] = {}

    async def add_comment(self, comment: Comment) -> Comment:
        if comment.id is None:
            # Приводим id к UUID, чтобы он согласовывался с API-роутами.
            from uuid import uuid4

            comment = comment.model_copy(update={"id": uuid4()})
        self._comments[comment.id] = comment
        return comment

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        return self._comments.get(comment_id)

    async def delete_comment(self, comment_id: UUID) -> bool:
        return self._comments.pop(comment_id, None) is not None

    async def get_comments_for_post(self, post_id: UUID) -> List[Comment]:
        return [c for c in self._comments.values() if c.post_id == post_id]
