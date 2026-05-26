from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.response import Response
from src.services.response_service import ResponseService


@pytest.mark.asyncio
async def test_add_response_publishes_kafka_event() -> None:
    repo = AsyncMock()
    kafka = AsyncMock()
    service = ResponseService(repo, kafka)
    response = Response(task_id=uuid4(), user_id=uuid4(), text="hello")
    repo.add_response.return_value = response

    created = await service.add_response(response)

    assert created == response
    kafka.send_response_add.assert_awaited_once_with(
        str(response.id), str(response.task_id), str(response.user_id)
    )


@pytest.mark.asyncio
async def test_delete_response_not_found_returns_false() -> None:
    repo = AsyncMock()
    kafka = AsyncMock()
    service = ResponseService(repo, kafka)
    repo.get_response.return_value = None

    deleted = await service.delete_response(uuid4())

    assert deleted is False
    kafka.send_response_delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_response_publishes_delete_event() -> None:
    repo = AsyncMock()
    kafka = AsyncMock()
    service = ResponseService(repo, kafka)
    response_id = uuid4()
    response = Response(task_id=uuid4(), user_id=uuid4(), text="bye")
    repo.get_response.return_value = response
    repo.delete_response.return_value = True

    deleted = await service.delete_response(response_id)

    assert deleted is True
    kafka.send_response_delete.assert_awaited_once_with(
        str(response_id), str(response.task_id)
    )
