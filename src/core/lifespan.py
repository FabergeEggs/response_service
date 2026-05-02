import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.core.logging import setup_logging
from src.repositories.in_memory_repositories import (
    InMemoryCommentRepository,
    InMemoryResponseRepository,
)
from src.services.comment_service import CommentService
from src.services.kafka_consumer import KafkaConsumerService
from src.services.kafka_producer import KafkaProducerService
from src.services.media_client import MediaServiceClient
from src.services.response_service import ResponseService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting Response Service...")

    # Repositories — created first, shared across services and consumer
    response_repo = InMemoryResponseRepository()
    comment_repo = InMemoryCommentRepository()

    # Infrastructure
    kafka_producer = KafkaProducerService()
    kafka_consumer = KafkaConsumerService(
        response_repo=response_repo,
        comment_repo=comment_repo,
    )
    media_client = MediaServiceClient(base_url=settings.MEDIA_SERVICE_URL)

    # Services
    response_service = ResponseService(response_repo, kafka_producer)
    comment_service = CommentService(comment_repo, response_repo)

    await kafka_producer.start()
    await kafka_consumer.start()
    logger.info("Kafka services started")

    consumer_task = asyncio.create_task(kafka_consumer.consume_loop())

    app.state.response_service = response_service
    app.state.comment_service = comment_service
    app.state.media_client = media_client

    yield

    logger.info("Shutting down Response Service...")

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        logger.info("Consumer loop cancelled")

    await kafka_consumer.stop()
    await kafka_producer.stop()
    await media_client.close()

    logger.info("All services stopped")
