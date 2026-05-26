from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.response import Response, ResponseStatus
from src.repositories.in_memory_repositories import InMemoryResponseRepository
from src.services.kafka_event_handler import KafkaEventHandler


class InMemoryDenormRepository:
    def __init__(self) -> None:
        self.users: set = set()
        self.user_names: dict = {}
        self.tasks: dict = {}
        self.posts: set = set()
        self.deleted_tasks: list = []
        self.deleted_posts: list = []

    async def upsert_user(self, user_id, name="") -> None:
        self.users.add(user_id)
        if name:
            self.user_names[user_id] = name

    async def upsert_task(self, task_id, project_id=None, project_status="ACTIVE") -> None:
        self.tasks[task_id] = project_status

    async def upsert_post(self, post_id, project_id=None, project_status="ACTIVE") -> None:
        self.posts.add(post_id)

    async def update_user(self, user_id, name=None) -> None:
        if name:
            self.user_names[user_id] = name

    async def get_user_names(self, user_ids):
        return {uid: self.user_names.get(uid, "") for uid in user_ids}

    async def update_task_status(self, task_id, project_status) -> None:
        self.tasks[task_id] = project_status

    async def delete_task(self, task_id) -> None:
        self.deleted_tasks.append(task_id)

    async def post_exists(self, post_id) -> bool:
        return post_id in self.posts

    async def delete_post(self, post_id) -> None:
        self.posts.discard(post_id)
        self.deleted_posts.append(post_id)


@pytest.mark.asyncio
async def test_task_deleted_removes_responses() -> None:
    repo = InMemoryResponseRepository()
    denorm = InMemoryDenormRepository()
    handler = KafkaEventHandler(repo, denorm)
    task_id = uuid4()
    response = Response(task_id=task_id, user_id=uuid4(), text="answer")
    await repo.add_response(response)

    await handler.delete_task({"task_id": str(task_id)})

    assert await repo.get_response(response.id) is None
    assert task_id in denorm.deleted_tasks


@pytest.mark.asyncio
async def test_task_deleted_no_responses_is_noop() -> None:
    repo = InMemoryResponseRepository()
    denorm = InMemoryDenormRepository()
    handler = KafkaEventHandler(repo, denorm)
    task_id = uuid4()

    await handler.delete_task({"task_id": str(task_id)})

    assert denorm.deleted_tasks == [task_id]


@pytest.mark.asyncio
async def test_task_deleted_missing_task_id_logs_warning(caplog) -> None:
    repo = InMemoryResponseRepository()
    handler = KafkaEventHandler(repo, InMemoryDenormRepository())

    await handler.delete_task({})

    assert "without task_id" in caplog.text


@pytest.mark.asyncio
async def test_task_deleted_does_not_touch_other_tasks() -> None:
    repo = InMemoryResponseRepository()
    handler = KafkaEventHandler(repo, InMemoryDenormRepository())
    task_a = uuid4()
    task_b = uuid4()
    response_a = Response(task_id=task_a, user_id=uuid4(), text="a")
    response_b = Response(task_id=task_b, user_id=uuid4(), text="b")
    await repo.add_response(response_a)
    await repo.add_response(response_b)

    await handler.delete_task({"task_id": str(task_a)})

    assert await repo.get_response(response_a.id) is None
    assert await repo.get_response(response_b.id) is not None


@pytest.mark.asyncio
async def test_task_changed_cancels_pending_responses_on_final_status() -> None:
    repo = InMemoryResponseRepository()
    handler = KafkaEventHandler(repo, InMemoryDenormRepository())
    task_id = uuid4()
    pending = Response(
        task_id=task_id, user_id=uuid4(), text="p", status=ResponseStatus.PENDING
    )
    accepted = Response(
        task_id=task_id, user_id=uuid4(), text="a", status=ResponseStatus.ACCEPTED
    )
    await repo.add_response(pending)
    await repo.add_response(accepted)

    await handler.change_task({"task_id": str(task_id), "status": "FINISHED"})

    updated_pending = await repo.get_response(pending.id)
    updated_accepted = await repo.get_response(accepted.id)
    assert updated_pending is not None
    assert updated_pending.status == ResponseStatus.CANCELLED
    assert updated_accepted is not None
    assert updated_accepted.status == ResponseStatus.ACCEPTED


@pytest.mark.asyncio
async def test_task_changed_non_final_status_no_cancellation() -> None:
    repo = InMemoryResponseRepository()
    handler = KafkaEventHandler(repo, InMemoryDenormRepository())
    task_id = uuid4()
    pending = Response(
        task_id=task_id, user_id=uuid4(), text="p", status=ResponseStatus.PENDING
    )
    await repo.add_response(pending)

    await handler.change_task({"task_id": str(task_id), "status": "ACTIVE"})

    updated = await repo.get_response(pending.id)
    assert updated is not None
    assert updated.status == ResponseStatus.PENDING


@pytest.mark.asyncio
async def test_task_changed_missing_task_id_logs_warning(caplog) -> None:
    handler = KafkaEventHandler(AsyncMock(), InMemoryDenormRepository())

    await handler.change_task({"status": "FINISHED"})

    assert "without task_id" in caplog.text


@pytest.mark.asyncio
async def test_user_registered_upserts_user() -> None:
    denorm = InMemoryDenormRepository()
    handler = KafkaEventHandler(AsyncMock(), denorm)
    user_id = uuid4()

    await handler.register_user(
        {
            "data": {
                "user_id": str(user_id),
                "first_name": "Ann",
                "last_name": "Bee",
                "email": "ann@example.com",
            }
        }
    )

    assert user_id in denorm.users
    assert denorm.user_names[user_id] == "Ann Bee"


@pytest.mark.asyncio
async def test_profile_changed_upserts_user() -> None:
    denorm = InMemoryDenormRepository()
    handler = KafkaEventHandler(AsyncMock(), denorm)
    user_id = uuid4()

    await handler.change_user(
        {"user_id": str(user_id), "changes": {"name": "Alice"}}
    )

    assert user_id in denorm.users


@pytest.mark.asyncio
async def test_task_created_upserts_task() -> None:
    denorm = InMemoryDenormRepository()
    handler = KafkaEventHandler(AsyncMock(), denorm)
    task_id = uuid4()

    await handler.create_task({"task_id": str(task_id), "project_id": str(uuid4())})

    assert task_id in denorm.tasks


@pytest.mark.asyncio
async def test_post_created_upserts_post() -> None:
    denorm = InMemoryDenormRepository()
    denorm.upsert_post = AsyncMock()
    handler = KafkaEventHandler(AsyncMock(), denorm)
    post_id = uuid4()

    await handler.create_post({"post_id": str(post_id)})

    denorm.upsert_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_changed_calls_upsert() -> None:
    denorm = InMemoryDenormRepository()
    denorm.upsert_post = AsyncMock()
    handler = KafkaEventHandler(AsyncMock(), denorm)
    post_id = uuid4()

    await handler.change_post({"post_id": str(post_id), "status": "ACTIVE"})

    denorm.upsert_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_deleted_removes_denorm_post() -> None:
    denorm = InMemoryDenormRepository()
    post_id = uuid4()
    await denorm.upsert_post(post_id)
    handler = KafkaEventHandler(AsyncMock(), denorm)

    await handler.delete_post({"post_id": str(post_id)})

    assert post_id in denorm.deleted_posts
    assert not await denorm.post_exists(post_id)
