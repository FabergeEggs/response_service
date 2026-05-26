from typing import Any, Optional

import pytest

from src.services.kafka_producer import KafkaProducerService


class DummyProducer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.started = False
        self.stopped = False
        self.sent: list[tuple[str, dict[str, Any], Optional[bytes]]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(self, topic: str, payload: dict[str, Any], key: bytes) -> None:
        self.sent.append((topic, payload, key))


@pytest.mark.asyncio
async def test_send_response_add_uses_expected_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.kafka_producer.AIOKafkaProducer", DummyProducer)
    service = KafkaProducerService()
    await service.start()

    await service.send_response_add("r1", "t1", "u1")

    sent = service._producer.sent  # type: ignore[union-attr]
    assert len(sent) == 2
    assert sent[0][0] == "response_service.response.add"
    assert sent[0][1]["response_id"] == "r1"
    assert sent[1][0] == "project-answers"
    assert sent[1][1]["type"] == "answer.created"
    assert sent[1][1]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_send_response_delete_uses_expected_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.kafka_producer.AIOKafkaProducer", DummyProducer)
    service = KafkaProducerService()
    await service.start()

    await service.send_response_delete("r2", "t2")

    sent = service._producer.sent  # type: ignore[union-attr]
    assert len(sent) == 2
    assert sent[0][0] == "response_service.response.delete"
    assert sent[0][1]["task_id"] == "t2"
    assert sent[1][0] == "project-answers"
    assert sent[1][1]["type"] == "answer.deleted"
