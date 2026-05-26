from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from src.services.kafka_consumer import KafkaConsumerService


class DummyMessage:
    def __init__(self, topic: str, value: bytes, key: Optional[bytes] = None) -> None:
        self.topic = topic
        self.value = value
        self.key = key


class DummyConsumer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.started = False
        self.stopped = False
        self._messages = [
            DummyMessage("project_service.task.created", b'{"task_id":"1"}', b"k1")
        ]

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def getone(self) -> DummyMessage:
        return self._messages.pop(0)


@pytest.mark.asyncio
async def test_dispatch_event_routes_to_expected_handler() -> None:
    service = KafkaConsumerService()
    handler = MagicMock()
    service._topic_handlers["project_service.task.created"] = handler

    await service._dispatch_event("project_service.task.created", "k", {"task_id": "1"})

    handler.assert_called_once_with({"task_id": "1"})


@pytest.mark.asyncio
async def test_consume_loop_consumes_and_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.kafka_consumer.AIOKafkaConsumer", DummyConsumer)
    service = KafkaConsumerService()
    await service.start()

    calls: list[tuple[str, Optional[str], dict[str, Any]]] = []

    async def fake_dispatch(topic: str, key: Optional[str], payload: dict[str, Any]) -> None:
        calls.append((topic, key, payload))
        service._running = False

    service._dispatch_event = fake_dispatch  # type: ignore[method-assign]
    await service.consume_loop()

    assert calls
    assert calls[0][0] == "project_service.task.created"
    assert calls[0][1] == "k1"
    assert calls[0][2]["task_id"] == "1"
