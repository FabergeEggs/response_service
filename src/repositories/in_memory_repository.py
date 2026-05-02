from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.models.comment import Comment
from src.models.response import Response, ResponseStatus


class InMemoryResponseRepository:
    def __init__(self) -> None:
        self._store: Dict[UUID, Response] = {}

    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        return [r for r in self._store.values() if r.task_id == task_id]

    async def get_response(self, response_id: UUID) -> Optional[Response]:
        return self._store.get(response_id)

    async def add_response(self, response: Response) -> Response:
        if response.id is None:
            response = response.model_copy(update={"id": uuid4()})
        self._store[response.id] = response
        return response

    async def change_response(
        self, response_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Response]:
        response = self._store.get(response_id)
        if not response:
            return None
        updated = response.model_copy(
            update={**update_data, "updated_at": datetime.now(timezone.utc)}
        )
        self._store[response_id] = updated
        return updated

    async def delete_response(self, response_id: UUID) -> bool:
        if response_id not in self._store:
            return False
        del self._store[response_id]
        return True

    async def change_response_status(
        self, response_id: UUID, status: ResponseStatus
    ) -> Optional[Response]:
        return await self.change_response(response_id, {"status": status})

    async def append_to_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        """Атомарно добавляет file_id к списку файлов."""
        response = self._store.get(response_id)
        if not response:
            return False
        if file_id in response.attached_files:
            return True  # уже есть — идемпотентно
        new_files = response.attached_files + [file_id]
        updated = response.model_copy(
            update={"attached_files": new_files, "updated_at": datetime.now(timezone.utc)}
        )
        self._store[response_id] = updated
        return True

    async def remove_from_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        """Атомарно удаляет file_id из списка файлов."""
        response = self._store.get(response_id)
        if not response or file_id not in response.attached_files:
            return False
        new_files = [fid for fid in response.attached_files if fid != file_id]
        updated = response.model_copy(
            update={"attached_files": new_files, "updated_at": datetime.now(timezone.utc)}
        )
        self._store[response_id] = updated
        return True


class InMemoryCommentRepository:
    def __init__(self) -> None:
        self._store: Dict[UUID, Comment] = {}

    async def add_comment(self, comment: Comment) -> Comment:
        if comment.id is None:
            comment = comment.model_copy(update={"id": uuid4()})
        self._store[comment.id] = comment
        return comment

    async def get_comment(self, comment_id: UUID) -> Optional[Comment]:
        return self._store.get(comment_id)

    async def delete_comment(self, comment_id: UUID) -> bool:
        if comment_id not in self._store:
            return False
        del self._store[comment_id]
        return True

    async def get_comments_for_response(self, response_id: UUID) -> List[Comment]:
        return [c for c in self._store.values() if c.response_id == response_id]
