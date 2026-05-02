import json
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

try:
    from aiokafka import AIOKafkaProducer as _AIOKafkaProducer
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    logger.warning("aiokafka not installed — KafkaProducerService runs in no-op mode")


class KafkaProducerService:
    """Реализует протокол KafkaProducer."""

    def __init__(self) -> None:
        self._producer = None

    async def start(self) -> None:
        if not _KAFKA_AVAILABLE:
            return
        self._producer = _AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def _send(self, topic: str, payload: dict) -> None:
        if not self._producer:
            logger.debug("Producer not running, skipping send to %s: %s", topic, payload)
            return
        try:
            await self._producer.send_and_wait(topic, payload)
            logger.debug("Sent to %s: %s", topic, payload)
        except Exception:
            logger.exception("Failed to send message to topic %s", topic)

    async def send_response_add(self, response_id: str, task_id: str, user_id: str) -> None:
        await self._send(
            settings.KAFKA_TOPIC_RESPONSE_ADD,
            {"response_id": response_id, "task_id": task_id, "user_id": user_id},
        )

    async def send_response_delete(self, response_id: str, task_id: str) -> None:
        await self._send(
            settings.KAFKA_TOPIC_RESPONSE_DELETE,
            {"response_id": response_id, "task_id": task_id},
        )
