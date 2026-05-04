from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
import logging
from src.repositories.in_memory_repositories import (
    InMemoryResponseRepository,
    InMemoryCommentRepository  # ← добавить этот
)
from src.services.kafka_consumer import KafkaConsumerService
from src.services.kafka_producer import KafkaProducerService
from src.services.media_client import MediaServiceClient
from src.services.response_service import ResponseService
from src.services.comment_service import CommentService
# Глобальные экземпляры (можно также хранить в app.state)
kafka_consumer = KafkaConsumerService()
kafka_producer = KafkaProducerService()
media_client = MediaServiceClient()

# Репозитории (временные in-memory)
response_repo = InMemoryResponseRepository()
comment_repo = InMemoryCommentRepository()

# Сервисы
response_service = ResponseService(response_repo, kafka_producer)
comment_service = CommentService(comment_repo, response_repo)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Настройка логгирования
    setup_logging()
    logger.info("Starting Response Service...")

    # Запуск Kafka producer и consumer
    await kafka_producer.start()
    await kafka_consumer.start()
    logger.info("Kafka services started")

    # Запуск фонового consumer loop
    consumer_task = asyncio.create_task(kafka_consumer.consume_loop())

    # Можно также сохранить сервисы в app.state для доступа в других местах (необязательно)
    app.state.response_service = response_service
    app.state.comment_service = comment_service
    app.state.media_client = media_client

    yield  # Здесь работает FastAPI

    # Shutdown
    logger.info("Shutting down...")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Consumer loop cancelled")

    await kafka_consumer.stop()
    await kafka_producer.stop()
    await media_client.close()
    logger.info("All services stopped")