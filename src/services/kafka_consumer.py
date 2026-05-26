import inspect
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Union

from aiokafka import AIOKafkaConsumer

from src.core.config import settings
from src.kafka_topics import (
    POST_CHANGED,
    POST_CREATED,
    POST_DELETE,
    PROFILE_CHANGED,
    TASK_CHANGED,
    TASK_CREATED,
    TASK_DELETE,
    USER_REGISTERED,
)

logger = logging.getLogger(__name__)

EventHandler = Callable[[Dict[str, Any]], Union[None, Awaitable[None]]]


class KafkaConsumerService:
    def __init__(
        self,
        event_handler: Optional[Any] = None,
    ) -> None:
        self._running = False
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._event_handler = event_handler
        self._topic_handlers: Dict[str, EventHandler] = self._build_topic_handlers()

    def _build_topic_handlers(self) -> Dict[str, EventHandler]:
        if self._event_handler is None:
            return {}

        handler = self._event_handler
        return {
            USER_REGISTERED: handler.register_user,
            PROFILE_CHANGED: handler.change_user,
            TASK_CREATED: handler.create_task,
            TASK_CHANGED: handler.change_task,
            TASK_DELETE: handler.delete_task,
            POST_CREATED: handler.create_post,
            POST_CHANGED: handler.change_post,
            POST_DELETE: handler.delete_post,
        }

    async def start(self) -> None:
        if self._consumer is not None:
            return
        consumer = AIOKafkaConsumer(
            *settings.KAFKA_TOPICS_INCOMING,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        try:
            await consumer.start()
        except Exception as exc:
            try:
                await consumer.stop()
            except Exception:
                pass
            logger.warning("Kafka consumer is unavailable: %s", exc)
            self._running = False
            return
        self._consumer = consumer
        self._running = True
        logger.info(
            "Kafka consumer started on %s, topics=%s",
            settings.KAFKA_BOOTSTRAP_SERVERS,
            settings.KAFKA_TOPICS_INCOMING,
        )

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        self._running = False
        logger.info("Kafka consumer stopped")

    async def consume_loop(self) -> None:
        if self._consumer is None:
            logger.warning("Kafka consumer loop skipped: consumer not started")
            return

        while self._running:
            message = await self._consumer.getone()
            payload_raw = message.value.decode("utf-8", errors="replace")
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload = {"raw": payload_raw}

            await self._dispatch_event(
                topic=message.topic,
                key=message.key.decode("utf-8", errors="replace") if message.key else None,
                payload=payload,
            )

    async def _dispatch_event(
        self, topic: str, key: Optional[str], payload: Dict[str, Any]
    ) -> None:
        handler = self._topic_handlers.get(topic)
        if handler is None:
            logger.warning("No handler for topic=%s key=%s payload=%s", topic, key, payload)
            return

        logger.info("Dispatching topic=%s key=%s", topic, key)
        result = handler(payload)
        if inspect.isawaitable(result):
            await result
