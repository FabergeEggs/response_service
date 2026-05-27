import logging
from typing import Any, Dict, Optional
from uuid import UUID

from src.models.response import ResponseStatus
from src.repositories.denorm_repository import DenormRepository
from src.repositories.response_repository import ResponseRepository

logger = logging.getLogger(__name__)

FINAL_TASK_STATUSES = {"FINISHED", "DELETED"}


def _parse_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _extract_task_id(payload: Dict[str, Any]) -> Optional[UUID]:
    for key in ("task_id", "id"):
        task_id = _parse_uuid(payload.get(key))
        if task_id is not None:
            return task_id
    return None


def _extract_post_id(payload: Dict[str, Any]) -> Optional[UUID]:
    for key in ("post_id", "id"):
        post_id = _parse_uuid(payload.get(key))
        if post_id is not None:
            return post_id
    return None


def _extract_display_name(payload: Dict[str, Any]) -> str:
    nested = payload.get("data")
    source = nested if isinstance(nested, dict) else payload
    first = str(source.get("first_name") or "").strip()
    last = str(source.get("last_name") or "").strip()
    name = f"{first} {last}".strip()
    if name:
        return name
    return str(source.get("email") or source.get("username") or "").strip()


def _extract_user_id(payload: Dict[str, Any]) -> Optional[UUID]:
    for key in ("user_id", "profile_id", "id"):
        user_id = _parse_uuid(payload.get(key))
        if user_id is not None:
            return user_id
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("user_id", "profile_id"):
            user_id = _parse_uuid(data.get(key))
            if user_id is not None:
                return user_id
    return None


class KafkaEventHandler:
    def __init__(
        self,
        response_repo: ResponseRepository,
        denorm_repo: DenormRepository,
    ) -> None:
        self._response_repo = response_repo
        self._denorm_repo = denorm_repo

    async def register_user(self, payload: Dict[str, Any]) -> None:
        user_id = _extract_user_id(payload)
        if user_id is None:
            logger.warning("user.registered without user_id: %s", payload)
            return

        name = _extract_display_name(payload)
        await self._denorm_repo.upsert_user(user_id, name=name)
        logger.info("Registered denormalized user %s", user_id)

    async def handle_user_event(self, payload: Dict[str, Any]) -> None:
        """Dispatcher for the multiplexed 'user-events' Kafka topic.

        profile_service publishes multiple event_types on this single topic:
        - "user.profile.updated" → update name in denorm cache
        - "user.avatar.updated"  → ignored (response_service doesn't use avatars)
        - "user.email.updated"   → ignored
        """
        event_type = payload.get("event_type", "")
        if event_type == "user.profile.updated":
            await self.change_user(payload)
        else:
            logger.debug("Ignoring user-event type=%s", event_type)

    async def change_user(self, payload: Dict[str, Any]) -> None:
        user_id = _extract_user_id(payload)
        if user_id is None:
            logger.warning("profile.changed without user_id: %s", payload)
            return

        # profile_service "user.profile.updated" sends {user_id, name} directly.
        # Older / legacy format uses {changes: {name: ...}} or {data: {changes: {name: ...}}}.
        name: Optional[str] = None
        if "name" in payload:
            name = str(payload["name"]).strip() or None
        else:
            changes = payload.get("changes", {})
            if not isinstance(changes, dict):
                changes = payload.get("data", {})
                if isinstance(changes, dict):
                    changes = changes.get("changes", {})
            name = changes.get("name") if isinstance(changes, dict) else None

        await self._denorm_repo.upsert_user(user_id)
        await self._denorm_repo.update_user(user_id, name=name)
        logger.info("Updated denormalized user %s", user_id)

    async def create_task(self, payload: Dict[str, Any]) -> None:
        task_id = _extract_task_id(payload)
        if task_id is None:
            logger.warning("task.created without task_id: %s", payload)
            return

        project_id = _parse_uuid(payload.get("project_id"))
        status = str(payload.get("status", "ACTIVE")).upper()
        await self._denorm_repo.upsert_task(task_id, project_id, status)
        logger.info("Upserted denormalized task %s", task_id)

    async def change_task(self, payload: Dict[str, Any]) -> None:
        task_id = _extract_task_id(payload)
        if task_id is None:
            logger.warning("task.changed without task_id: %s", payload)
            return

        status = str(payload.get("status", "")).upper()
        project_id = _parse_uuid(payload.get("project_id"))
        if status:
            await self._denorm_repo.upsert_task(task_id, project_id, status)
            await self._denorm_repo.update_task_status(task_id, status)

        if status in FINAL_TASK_STATUSES:
            cancelled = await self._response_repo.cancel_pending_by_task_id(task_id)
            logger.info(
                "Cancelled %s pending responses for task %s (status=%s)",
                cancelled,
                task_id,
                status,
            )

    async def delete_task(self, payload: Dict[str, Any]) -> None:
        task_id = _extract_task_id(payload)
        if task_id is None:
            logger.warning("task.deleted without task_id: %s", payload)
            return

        deleted = await self._response_repo.delete_responses_by_task_id(task_id)
        await self._denorm_repo.delete_task(task_id)
        logger.info("Deleted %s responses for task %s", deleted, task_id)

    async def create_post(self, payload: Dict[str, Any]) -> None:
        post_id = _extract_post_id(payload)
        if post_id is None:
            logger.warning("post.created without post_id: %s", payload)
            return

        project_id = _parse_uuid(payload.get("project_id"))
        await self._denorm_repo.upsert_post(post_id, project_id)
        logger.info("Upserted denormalized post %s", post_id)

    async def change_post(self, payload: Dict[str, Any]) -> None:
        post_id = _extract_post_id(payload)
        if post_id is None:
            logger.warning("post.changed without post_id: %s", payload)
            return

        project_id = _parse_uuid(payload.get("project_id"))
        status = str(payload.get("status", "ACTIVE")).upper()
        await self._denorm_repo.upsert_post(post_id, project_id, status)

    async def delete_post(self, payload: Dict[str, Any]) -> None:
        post_id = _extract_post_id(payload)
        if post_id is None:
            logger.warning("post.deleted without post_id: %s", payload)
            return
        await self._denorm_repo.delete_post(post_id)
        logger.info("Deleted denormalized post %s and its comments", post_id)
