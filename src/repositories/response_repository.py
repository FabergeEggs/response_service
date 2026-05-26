from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.models.response import Response, ResponseStatus


class ResponseRepository(ABC):
    @abstractmethod
    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        raise NotImplementedError

    @abstractmethod
    async def get_response(self, response_id: UUID) -> Optional[Response]:
        raise NotImplementedError

    @abstractmethod
    async def add_response(self, response: Response) -> Response:
        raise NotImplementedError

    @abstractmethod
    async def change_response(
        self, response_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Response]:
        raise NotImplementedError

    @abstractmethod
    async def delete_response(self, response_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def change_response_status(
        self, response_id: UUID, status: ResponseStatus
    ) -> Optional[Response]:
        raise NotImplementedError

    @abstractmethod
    async def append_to_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def remove_from_attached_files(self, response_id: UUID, file_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete_responses_by_task_id(self, task_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def cancel_pending_by_task_id(self, task_id: UUID) -> int:
        raise NotImplementedError
