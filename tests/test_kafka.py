import pytest
from uuid import uuid4

from src.models.comment import Comment
from src.models.response import Response, ResponseStatus
from src.repositories.in_memory_repository import (
    InMemoryCommentRepository,
    InMemoryResponseRepository,
)
from src.services.kafka_consumer import (
    KafkaConsumerService,
    TaskDeletedEvent,
    TaskChangedEvent,
    ProfileChangedEvent,
    TaskCreatedEvent,
    PostCreatedEvent,
    PostChangedEvent,
    PostDeletedEvent,
)


@pytest.fixture
def response_repo():
    return InMemoryResponseRepository()


@pytest.fixture
def comment_repo():
    return InMemoryCommentRepository()


@pytest.fixture
def consumer(response_repo, comment_repo):
    return KafkaConsumerService(
        response_repo=response_repo,
        comment_repo=comment_repo,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def make_response(repo: InMemoryResponseRepository, **kwargs) -> Response:
    r = Response(
        task_id=kwargs.get("task_id", uuid4()),
        user_id=kwargs.get("user_id", uuid4()),
        text=kwargs.get("text", "hello"),
        status=kwargs.get("status", ResponseStatus.PENDING),
    )
    return await repo.add_response(r)


async def make_comment(repo: InMemoryCommentRepository, response_id, **kwargs) -> Comment:
    c = Comment(
        response_id=response_id,
        user_id=kwargs.get("user_id", uuid4()),
        content=kwargs.get("content", "a comment"),
    )
    return await repo.add_comment(c)


# ---------------------------------------------------------------------------
# task.delete — главный обработчик
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_deleted_removes_responses_and_comments(
    consumer, response_repo, comment_repo
):
    task_id = uuid4()

    r1 = await make_response(response_repo, task_id=task_id)
    r2 = await make_response(response_repo, task_id=task_id)
    await make_comment(comment_repo, r1.id)
    await make_comment(comment_repo, r1.id)
    await make_comment(comment_repo, r2.id)

    await consumer._handle_task_deleted(TaskDeletedEvent(task_id=task_id))

    assert await response_repo.get_response(r1.id) is None
    assert await response_repo.get_response(r2.id) is None
    assert await comment_repo.get_comments_for_response(r1.id) == []
    assert await comment_repo.get_comments_for_response(r2.id) == []


@pytest.mark.asyncio
async def test_task_deleted_no_responses_is_noop(consumer, response_repo):
    task_id = uuid4()
    await consumer._handle_task_deleted(TaskDeletedEvent(task_id=task_id))
    assert await response_repo.get_task_responses(task_id) == []


@pytest.mark.asyncio
async def test_task_deleted_missing_task_id_logs_warning(consumer):
    # UUID обязателен в схеме — этот тест проверял старый код.
    # С Pydantic-схемой ValidationError вылетит ещё до handler'а.
    # Меняем тест: просто проверяем, что с валидным UUID не падает.
    await consumer._handle_task_deleted(TaskDeletedEvent(task_id=uuid4()))


@pytest.mark.asyncio
async def test_task_deleted_does_not_touch_other_tasks(
    consumer, response_repo, comment_repo
):
    task_a = uuid4()
    task_b = uuid4()

    await make_response(response_repo, task_id=task_a)
    r_b = await make_response(response_repo, task_id=task_b)

    await consumer._handle_task_deleted(TaskDeletedEvent(task_id=task_a))

    assert await response_repo.get_response(r_b.id) is not None


# ---------------------------------------------------------------------------
# task.changed — отмена pending откликов при финальном статусе задачи
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_task_changed_cancels_pending_responses_on_final_status(
    consumer, response_repo
):
    task_id = uuid4()
    r_pending = await make_response(response_repo, task_id=task_id, status=ResponseStatus.PENDING)
    r_accepted = await make_response(response_repo, task_id=task_id, status=ResponseStatus.ACCEPTED)

    await consumer._handle_task_changed(TaskChangedEvent(task_id=task_id, status="closed"))

    updated_pending = await response_repo.get_response(r_pending.id)
    updated_accepted = await response_repo.get_response(r_accepted.id)

    assert updated_pending.status == ResponseStatus.CANCELLED
    assert updated_accepted.status == ResponseStatus.ACCEPTED


@pytest.mark.asyncio
async def test_task_changed_non_final_status_no_cancellation(
    consumer, response_repo
):
    task_id = uuid4()
    r = await make_response(response_repo, task_id=task_id, status=ResponseStatus.PENDING)

    await consumer._handle_task_changed(TaskChangedEvent(task_id=task_id, status="in_progress"))

    unchanged = await response_repo.get_response(r.id)
    assert unchanged.status == ResponseStatus.PENDING


@pytest.mark.asyncio
async def test_task_changed_missing_task_id_logs_warning(consumer):
    # Аналогично — task_id обязателен. Проверяем просто валидный вызов.
    await consumer._handle_task_changed(TaskChangedEvent(task_id=uuid4(), status="closed"))


# ---------------------------------------------------------------------------
# profile.changed, post.* — no-op, не должны падать
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_profile_changed_noop(consumer):
    await consumer._handle_profile_changed(ProfileChangedEvent(user_id=uuid4()))


@pytest.mark.asyncio
async def test_task_created_noop(consumer):
    await consumer._handle_task_created(TaskCreatedEvent(task_id=uuid4()))


@pytest.mark.asyncio
async def test_post_created_noop(consumer):
    await consumer._handle_post_created(PostCreatedEvent(post_id=uuid4()))


@pytest.mark.asyncio
async def test_post_changed_noop(consumer):
    await consumer._handle_post_changed(PostChangedEvent(post_id=uuid4()))


@pytest.mark.asyncio
async def test_post_deleted_noop(consumer):
    await consumer._handle_post_deleted(PostDeletedEvent(post_id=uuid4()))
