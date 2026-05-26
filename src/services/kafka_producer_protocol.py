from typing import Protocol


class KafkaProducer(Protocol):
    async def send_response_add(self, response_id: str, task_id: str, user_id: str) -> None:
        ...

    async def send_response_delete(self, response_id: str, task_id: str) -> None:
        ...
