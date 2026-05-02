import logging
from uuid import UUID
from typing import List, Optional, Dict, Any

from src.models.response import Response, ResponseStatus
from src.repositories.response_repository import ResponseRepository
from src.services.kafka_producer_protocol import KafkaProducer  # ← протокол, не реализация

logger = logging.getLogger(__name__)


class ResponseService:
    def __init__(self, response_repo: ResponseRepository, kafka_producer: KafkaProducer):
        self._repo = response_repo
        self._kafka = kafka_producer

    async def get_task_responses(self, task_id: UUID) -> List[Response]:
        logger.debug("Fetching responses for task %s", task_id)
        return await self._repo.get_task_responses(task_id)

    async def get_response(self, response_id: UUID) -> Optional[Response]:
        return await self._repo.get_response(response_id)

    async def add_response(self, response: Response) -> Response:
        created = await self._repo.add_response(response)
        logger.info(
            "Response %s created for task %s by user %s",
            created.id, created.task_id, created.user_id,
        )
        await self._kafka.send_response_add(
            str(created.id), str(created.task_id), str(created.user_id)
        )
        return created

    async def change_response(
        self, response_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Response]:
        updated = await self._repo.change_response(response_id, update_data)
        if updated:
            logger.info(
                "Response %s updated with fields: %s",
                response_id, list(update_data.keys()),
            )
        else:
            logger.warning("Response %s not found for update", response_id)
        return updated

    async def delete_response(self, response_id: UUID) -> bool:
        """Удаляет отклик и публикует событие.

        Сначала пробуем удалить через репозиторий — это атомарная операция.
        Kafka-событие отправляем только при успехе, используя task_id из
        удалённого объекта, который возвращает репозиторий.
        """
        # Получаем task_id до удаления, чтобы включить его в Kafka-событие.
        # Две отдельные операции (get + delete) создают потенциальный TOCTOU,
        # поэтому делаем get только для чтения метаданных, а факт существования
        # определяем по результату delete.
        response = await self._repo.get_response(response_id)
        if not response:
            logger.warning("Response %s not found for deletion", response_id)
            return False

        deleted = await self._repo.delete_response(response_id)
        if deleted:
            logger.info("Response %s deleted", response_id)
            await self._kafka.send_response_delete(str(response_id), str(response.task_id))
        return deleted

    async def change_response_status(
        self, response_id: UUID, status: ResponseStatus
    ) -> Optional[Response]:
        updated = await self._repo.change_response_status(response_id, status)
        if updated:
            logger.info("Response %s status changed to %s", response_id, status)
        else:
            logger.warning("Response %s not found for status change", response_id)
        return updated

    async def add_file_to_response(self, response_id: UUID, file_id: UUID) -> bool:
        """Атомарно добавляет file_id к списку attached_files отклика."""
        return await self._repo.append_to_attached_files(response_id, file_id)

    async def remove_file_from_response(self, response_id: UUID, file_id: UUID) -> bool:
        """Атомарно удаляет file_id из списка attached_files отклика."""
        return await self._repo.remove_from_attached_files(response_id, file_id)
