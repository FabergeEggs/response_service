import json
import logging
from typing import Optional

from aiokafka import AIOKafkaProducer

from src.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        try:
            await producer.start()
        except Exception as exc:
            try:
                await producer.stop()
            except Exception:
                pass
            logger.warning("Kafka producer is unavailable: %s", exc)
            return
        self._producer = producer
        logger.info(
            "Kafka producer started on %s", settings.KAFKA_BOOTSTRAP_SERVERS
        )

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
        logger.info("Kafka producer stopped")

    async def _publish_answer_event(
        self,
        event_type: str,
        response_id: str,
        task_id: str,
        user_id: str | None = None,
    ) -> None:
        if self._producer is None:
            logger.warning(
                "Skip publish %s: producer not started", settings.KAFKA_TOPIC_ANSWERS
            )
            return

        payload: dict = {
            "type": event_type,
            "task_id": task_id,
            "response_id": response_id,
        }
        if user_id is not None:
            payload["user_id"] = user_id

        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_ANSWERS,
            payload,
            key=response_id.encode("utf-8"),
        )
        logger.info(
            "Published %s on %s for response %s",
            event_type,
            settings.KAFKA_TOPIC_ANSWERS,
            response_id,
        )

    async def send_response_add(self, response_id: str, task_id: str, user_id: str) -> None:
        if self._producer is None:
            logger.warning(
                "Skip publish %s: producer not started",
                settings.KAFKA_TOPIC_RESPONSE_ADD,
            )
            return

        payload = {
            "response_id": response_id,
            "task_id": task_id,
            "user_id": user_id,
        }
        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_RESPONSE_ADD,
            payload,
            key=response_id.encode("utf-8"),
        )
        logger.info(
            "Published event %s for response %s",
            settings.KAFKA_TOPIC_RESPONSE_ADD,
            response_id,
        )
        await self._publish_answer_event(
            "answer.created", response_id, task_id, user_id
        )

    async def send_response_delete(self, response_id: str, task_id: str) -> None:
        if self._producer is None:
            logger.warning(
                "Skip publish %s: producer not started",
                settings.KAFKA_TOPIC_RESPONSE_DELETE,
            )
            return

        payload = {
            "response_id": response_id,
            "task_id": task_id,
        }
        await self._producer.send_and_wait(
            settings.KAFKA_TOPIC_RESPONSE_DELETE,
            payload,
            key=response_id.encode("utf-8"),
        )
        logger.info(
            "Published event %s for response %s",
            settings.KAFKA_TOPIC_RESPONSE_DELETE,
            response_id,
        )
        await self._publish_answer_event(
            "answer.deleted", response_id, task_id
        )
