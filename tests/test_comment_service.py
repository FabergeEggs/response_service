from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.comment import Comment
from src.services.comment_service import CommentService


@pytest.mark.asyncio
async def test_add_comment_returns_none_if_post_absent() -> None:
    comment_repo = AsyncMock()
    denorm_repo = AsyncMock()
    denorm_repo.post_exists.return_value = False
    service = CommentService(comment_repo, denorm_repo)

    result = await service.add_comment(
        uuid4(), Comment(post_id=uuid4(), user_id=uuid4(), content="x")
    )

    assert result is None
    comment_repo.add_comment.assert_not_called()


@pytest.mark.asyncio
async def test_add_comment_uses_provided_post_id() -> None:
    comment_repo = AsyncMock()
    denorm_repo = AsyncMock()
    denorm_repo.post_exists.return_value = True
    requested_post_id = uuid4()
    kafka_producer = AsyncMock()
    service = CommentService(comment_repo, denorm_repo, kafka_producer)

    original_comment = Comment(
        post_id=uuid4(),
        user_id=uuid4(),
        content="new comment",
    )
    expected = original_comment.model_copy(update={"post_id": requested_post_id})
    expected = expected.model_copy(update={"id": uuid4()})
    comment_repo.add_comment.return_value = expected

    created = await service.add_comment(requested_post_id, original_comment)

    assert created is not None
    assert created.post_id == requested_post_id
    kafka_producer.send_comment_created.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_post_comments_attaches_user_name() -> None:
    comment_repo = AsyncMock()
    denorm_repo = AsyncMock()
    denorm_repo.post_exists.return_value = True
    post_id = uuid4()
    user_id = uuid4()
    comment = Comment(post_id=post_id, user_id=user_id, content="hi")
    comment_repo.get_comments_for_post.return_value = [comment]
    denorm_repo.get_user_names.return_value = {user_id: "Alice"}

    service = CommentService(comment_repo, denorm_repo)
    result = await service.get_post_comments(post_id)

    assert result is not None
    assert len(result) == 1
    assert result[0].user_name == "Alice"


@pytest.mark.asyncio
async def test_get_post_comments_returns_none_if_post_missing() -> None:
    comment_repo = AsyncMock()
    denorm_repo = AsyncMock()
    denorm_repo.post_exists.return_value = False
    service = CommentService(comment_repo, denorm_repo)

    result = await service.get_post_comments(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_delete_comment_publishes_kafka_event() -> None:
    comment_repo = AsyncMock()
    denorm_repo = AsyncMock()
    kafka_producer = AsyncMock()
    comment_id = uuid4()
    post_id = uuid4()
    comment_repo.get_comment.return_value = Comment(
        id=comment_id, post_id=post_id, user_id=uuid4(), content="x"
    )
    comment_repo.delete_comment.return_value = True
    service = CommentService(comment_repo, denorm_repo, kafka_producer)

    deleted = await service.delete_comment(comment_id)

    assert deleted is True
    kafka_producer.send_comment_deleted.assert_awaited_once_with(
        str(comment_id), str(post_id)
    )
