import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.core.config import settings
from src.repositories.comment_repository import CommentRepository
from src.repositories.response_repository import ResponseRepository
from src.models.response import ResponseStatus

logger = logging.getLogger(__name__)

try:
    from aiokafka import AIOKafkaConsumer as _AIOKafkaConsumer
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    logger.warning("aiokafka not installed — KafkaConsumerService runs in no-op mode")


# ─── Pydantic-схемы для входящих событий ───────────────────────────────────

class ProfileChangedEvent(BaseModel):
    user_id: UUID

class TaskCreatedEvent(BaseModel):
    task_id: UUID

class TaskChangedEvent(BaseModel):
    task_id: UUID
    status: Optional[str] = None

class TaskDeletedEvent(BaseModel):
    task_id: UUID

class PostCreatedEvent(BaseModel):
    post_id: UUID

class PostChangedEvent(BaseModel):
    post_id: UUID

class PostDeletedEvent(BaseModel):
    post_id: UUID


# ─── Маппинг топик → (схема, handler) ──────────────────────────────────────

TOPIC_CONFIG = {
    "profile_service.profile.changed": (ProfileChangedEvent, "_handle_profile_changed"),
    "project_service.task.created":    (TaskCreatedEvent,    "_handle_task_created"),
    "project_service.task.changed":    (TaskChangedEvent,    "_handle_task_changed"),
    "project_service.task.delete":     (TaskDeletedEvent,    "_handle_task_deleted"),
    "project_service.post.created":    (PostCreatedEvent,    "_handle_post_created"),
    "project_service.post.changed":    (PostChangedEvent,    "_handle_post_changed"),
    "project_service.post.delete":     (PostDeletedEvent,    "_handle_post_deleted"),
}

FINAL_TASK_STATUSES = {"closed", "archived", "cancelled"}


class KafkaConsumerService:
    """Слушает входящие события от profile и project сервисов."""

    def __init__(
        self,
        response_repo: ResponseRepository,
        comment_repo: CommentRepository,
        max_processed_ids: int = 100_000,
    ) -> None:
        self._response_repo = response_repo
        self._comment_repo = comment_repo
        self._consumer = None
        # Простейшая идемпотентность: храним обработанные ключи (topic:partition:offset)
        self._processed_offsets: Set[str] = set()
        self._max_processed = max_processed_ids

    def _make_offset_key(self, topic: str, partition: int, offset: int) -> str:
        return f"{topic}:{partition}:{offset}"

    def _mark_processed(self, key: str) -> None:
        if len(self._processed_offsets) >= self._max_processed:
            # Очистка старых ключей (упрощённо — сбрасываем половину)
            self._processed_offsets = set(list(self._processed_offsets)[self._max_processed // 2:])
        self._processed_offsets.add(key)

    async def start(self) -> None:
        if not _KAFKA_AVAILABLE:
            return
        self._consumer = _AIOKafkaConsumer(
            *settings.KAFKA_TOPICS_INCOMING,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        logger.info("Kafka consumer started, topics: %s", settings.KAFKA_TOPICS_INCOMING)

    async def stop(self) -> None:
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume_loop(self) -> None:
        if not self._consumer:
            logger.info("Consumer not running (no-op mode)")
            await asyncio.Future()
            return

        async for msg in self._consumer:
            topic: str = msg.topic
            offset_key = self._make_offset_key(topic, msg.partition, msg.offset)

            if offset_key in self._processed_offsets:
                logger.debug("Skipping duplicate: %s", offset_key)
                continue

            payload: Dict[str, Any] = msg.value
            logger.debug("Received [%s]: %s", topic, payload)

            config = TOPIC_CONFIG.get(topic)
            if not config:
                logger.warning("No handler for topic: %s", topic)
                self._mark_processed(offset_key)
                continue

            schema, handler_name = config
            try:
                event = schema(**payload)
            except ValidationError as e:
                logger.error("Invalid payload for topic %s: %s — payload: %s", topic, e, payload)
                self._mark_processed(offset_key)
                continue

            handler = getattr(self, handler_name, None)
            if handler is None:
                logger.error("Handler method not found: %s", handler_name)
                self._mark_processed(offset_key)
                continue

            try:
                await handler(event)
            except Exception:
                logger.exception("Error in handler %s, event=%s", handler_name, event)

            self._mark_processed(offset_key)

    # ─── Обработчики ───────────────────────────────────────────────────────

    async def _handle_profile_changed(self, event: ProfileChangedEvent) -> None:
        logger.info("profile.changed user_id=%s — no local state to update", event.user_id)

    async def _handle_task_created(self, event: TaskCreatedEvent) -> None:
        logger.info("task.created task_id=%s — no action needed", event.task_id)

    async def _handle_task_changed(self, event: TaskChangedEvent) -> None:
        if event.status not in FINAL_TASK_STATUSES:
            logger.info("task.changed task_id=%s status=%s — no action", event.task_id, event.status)
            return

        responses = await self._response_repo.get_task_responses(event.task_id)
        cancelled = 0
        for response in responses:
            if response.status == ResponseStatus.PENDING:
                await self._response_repo.change_response_status(response.id, ResponseStatus.CANCELLED)
                cancelled += 1

        logger.info(
            "task.changed task_id=%s status=%s — cancelled %d pending responses",
            event.task_id, event.status, cancelled,
        )

    async def _handle_task_deleted(self, event: TaskDeletedEvent) -> None:
        responses = await self._response_repo.get_task_responses(event.task_id)

        if not responses:
            logger.info("task.delete task_id=%s — no responses to clean up", event.task_id)
            return

        deleted_comments = 0
        deleted_responses = 0

        for response in responses:
            comments = await self._comment_repo.get_comments_for_response(response.id)
            for comment in comments:
                await self._comment_repo.delete_comment(comment.id)
                deleted_comments += 1
            await self._response_repo.delete_response(response.id)
            deleted_responses += 1

        logger.info(
            "task.delete task_id=%s — deleted %d responses, %d comments",
            event.task_id, deleted_responses, deleted_comments,
        )

    async def _handle_post_created(self, event: PostCreatedEvent) -> None:
        logger.info("post.created post_id=%s — no action needed", event.post_id)

    async def _handle_post_changed(self, event: PostChangedEvent) -> None:
        logger.info("post.changed post_id=%s — no action needed", event.post_id)

    async def _handle_post_deleted(self, event: PostDeletedEvent) -> None:
        logger.info("post.deleted post_id=%s — no action needed", event.post_id)
