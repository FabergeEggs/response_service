from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi import FastAPI

from src.core.config import settings
from src.core.db import create_pool
from src.core.logging import setup_logging
from src.migrations import migrate
from src.repositories.postgres_comment_repository import PostgresCommentRepository
from src.repositories.postgres_denorm_repository import PostgresDenormRepository
from src.repositories.postgres_response_repository import PostgresResponseRepository
from src.services.kafka_consumer import KafkaConsumerService
from src.services.kafka_event_handler import KafkaEventHandler
from src.services.kafka_producer import KafkaProducerService
from src.services.media_client import MediaServiceClient
from src.services.response_service import ResponseService
from src.services.comment_service import CommentService

kafka_producer = KafkaProducerService()
media_client = MediaServiceClient()

logger = logging.getLogger(__name__)


def _get_migrations_dsn() -> str:
    dsn = settings.MIGRATIONS_DATABASE_URL
    if dsn:
        return dsn
    # Fallback: convert SQLAlchemy async DSN to sync DSN format for yoyo.
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Настройка логгирования
    setup_logging()
    logger.info("Starting Response Service...")

    if settings.RUN_DB_MIGRATIONS_ON_STARTUP:
        try:
            migrations_dsn = _get_migrations_dsn()
            migrate.up(migrations_dsn)
            logger.info("Database migrations applied from ./migrations")
        except Exception as exc:
            # Keep service bootable in environments where DB is temporarily unavailable.
            logger.warning("Failed to apply database migrations: %s", exc)

    await kafka_producer.start()
    logger.info("Kafka producer started")

    db_pool = await create_pool()
    response_repo = PostgresResponseRepository(db_pool)
    comment_repo = PostgresCommentRepository(db_pool)
    denorm_repo = PostgresDenormRepository(db_pool)
    event_handler = KafkaEventHandler(response_repo, denorm_repo)
    kafka_consumer = KafkaConsumerService(event_handler=event_handler)
    await kafka_consumer.start()

    response_service = ResponseService(response_repo, kafka_producer, denorm_repo)
    comment_service = CommentService(
        comment_repo, denorm_repo, kafka_producer
    )

    # Запуск фонового consumer loop
    consumer_task = asyncio.create_task(kafka_consumer.consume_loop())

    # Можно также сохранить сервисы в app.state для доступа в других местах (необязательно)
    app.state.response_service = response_service
    app.state.comment_service = comment_service
    app.state.media_client = media_client
    app.state.db_pool = db_pool

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
    await db_pool.close()
    await media_client.close()
    logger.info("All services stopped")