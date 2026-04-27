from uuid import UUID
from typing import List, Optional, Dict, Any
from src.models.response import Response, ResponseStatus
from src.repositories.response_repository import ResponseRepository
from src.services.kafka_producer import KafkaProducerService


class ResponseService:
    def __init__(self, response_repo: ResponseRepository, kafka_producer: KafkaProducerService):
        self._repo = response_repo
        self._kafka = kafka_producer

    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        return await self._repo.get_task_responses(task_id)

    async def get_response(self, response_id: UUID) -> Optional[Response]:
        return await self._repo.get_response(response_id)

    async def add_response(self, response: Response) -> Response:
        created = await self._repo.add_response(response)
        # Отправка Kafka события
        await self._kafka.send_response_add(str(created.id), str(created.task_id), str(created.user_id))
        return created

    async def change_response(self, response_id: UUID, update_data: Dict[str, Any]) -> Optional[Response]:
        updated = await self._repo.change_response(response_id, update_data)
        # Если нужно, можно слать событие об изменении (в схеме не было, но можно добавить)
        return updated

    async def delete_response(self, response_id: UUID) -> bool:
        response = await self._repo.get_response(response_id)
        if not response:
            return False
        deleted = await self._repo.delete_response(response_id)
        if deleted:
            await self._kafka.send_response_delete(str(response_id), str(response.task_id))
        return deleted

    async def change_response_status(self, response_id: UUID, status: ResponseStatus) -> Optional[Response]:
        return await self._repo.change_response_status(response_id, status)