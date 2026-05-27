from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID


class DenormRepository(ABC):
    @abstractmethod
    async def upsert_user(self, user_id: UUID, name: str = "") -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_task(
        self,
        task_id: UUID,
        project_id: Optional[UUID] = None,
        project_status: str = "ACTIVE",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_post(
        self,
        post_id: UUID,
        project_id: Optional[UUID] = None,
        project_status: str = "ACTIVE",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: UUID, name: Optional[str] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_user_names(self, user_ids: List[UUID]) -> Dict[UUID, str]:
        raise NotImplementedError

    @abstractmethod
    async def update_task_status(self, task_id: UUID, project_status: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_task(self, task_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def post_exists(self, post_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete_post(self, post_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_task_project_id(self, task_id: UUID) -> Optional[UUID]:
        """Return the project_id for a denormalized task, or None if not found."""
        raise NotImplementedError
