from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.comment import Comment
from src.models.response import Response
from src.services.comment_service import CommentService


@pytest.mark.asyncio
async def test_add_comment_returns_none_if_response_absent() -> None:
    comment_repo = AsyncMock()
    response_repo = AsyncMock()
    response_repo.get_response.return_value = None
    service = CommentService(comment_repo, response_repo)

    result = await service.add_comment(
        uuid4(), Comment(response_id=uuid4(), user_id=uuid4(), content="x")
    )

    assert result is None
    comment_repo.add_comment.assert_not_called()


@pytest.mark.asyncio
async def test_add_comment_uses_provided_response_id() -> None:
    comment_repo = AsyncMock()
    response_repo = AsyncMock()
    response_repo.get_response.return_value = Response(
        task_id=uuid4(), user_id=uuid4(), text="r"
    )
    service = CommentService(comment_repo, response_repo)
    requested_response_id = uuid4()
    original_comment = Comment(
        response_id=uuid4(),
        user_id=uuid4(),
        content="new comment",
    )
    expected = original_comment.model_copy(update={"response_id": requested_response_id})
    comment_repo.add_comment.return_value = expected

    created = await service.add_comment(requested_response_id, original_comment)

    assert created is not None
    assert created.response_id == requested_response_id


@pytest.mark.asyncio
async def test_get_response_comments_attaches_user_name() -> None:
    comment_repo = AsyncMock()
    response_repo = AsyncMock()
    denorm_repo = AsyncMock()
    user_id = uuid4()
    response_id = uuid4()
    response_repo.get_response.return_value = Response(
        task_id=uuid4(), user_id=uuid4(), text="r"
    )
    comment = Comment(response_id=response_id, user_id=user_id, content="hi")
    comment_repo.get_comments_for_response.return_value = [comment]
    denorm_repo.get_user_names.return_value = {user_id: "Ann Bee"}

    service = CommentService(comment_repo, response_repo, denorm_repo)
    result = await service.get_response_comments(response_id)

    assert result is not None
    assert len(result) == 1
    assert result[0].user_name == "Ann Bee"
    denorm_repo.get_user_names.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_response_comments_returns_none_if_response_missing() -> None:
    comment_repo = AsyncMock()
    response_repo = AsyncMock()
    response_repo.get_response.return_value = None
    service = CommentService(comment_repo, response_repo)

    result = await service.get_response_comments(uuid4())

    assert result is None
