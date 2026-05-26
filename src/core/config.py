from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

from src.kafka_topics import ANSWERS, INCOMING_TOPICS, RESPONSE_ADD, RESPONSE_DELETE

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    HOST: str = Field(default="0.0.0.0", description="Host to bind")
    PORT: int = Field(default=8000, description="Port to bind")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    KAFKA_CONSUMER_GROUP: str = Field(default="response-service-group")

    # Incoming topics (from profile and project services)
    KAFKA_TOPICS_INCOMING: List[str] = Field(default=INCOMING_TOPICS)

    # Outgoing topics
    KAFKA_TOPIC_RESPONSE_ADD: str = Field(default=RESPONSE_ADD)
    KAFKA_TOPIC_RESPONSE_DELETE: str = Field(default=RESPONSE_DELETE)
    KAFKA_TOPIC_ANSWERS: str = Field(
        default=ANSWERS,
        description="Topic for project_service answer counters",
    )

    # Media Service
    MEDIA_SERVICE_URL: str = Field(default="http://media-service:8000")

    # Database (not implemented yet)
    DATABASE_URL: str = Field(default="postgresql+asyncpg://user:pass@db:5432/response_db")
    MIGRATIONS_DATABASE_URL: str = Field(
        default="postgresql://user:pass@db:5432/response_db",
        description="Sync DSN for yoyo migrations",
    )
    RUN_DB_MIGRATIONS_ON_STARTUP: bool = Field(
        default=True,
        description="Run yoyo migrations from ./migrations on app startup",
    )

settings = Settings()