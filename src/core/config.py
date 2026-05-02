from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    HOST: str = Field(default="0.0.0.0", description="Host to bind")
    PORT: int = Field(default=8000, description="Port to bind")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092")
    KAFKA_CONSUMER_GROUP: str = Field(default="response-service-group")

    KAFKA_TOPICS_INCOMING: List[str] = Field(default=[
        "profile_service.profile.changed",
        "project_service.task.created",
        "project_service.task.changed",
        "project_service.task.delete",
        "project_service.post.created",
        "project_service.post.changed",
        "project_service.post.delete",
    ])

    KAFKA_TOPIC_RESPONSE_ADD: str = Field(default="response_service.response.add")
    KAFKA_TOPIC_RESPONSE_DELETE: str = Field(default="response_service.response.delete")

    MEDIA_SERVICE_URL: str = Field(default="http://media-service:8000")

    DATABASE_URL: str = Field(default="postgresql+asyncpg://user:pass@db:5432/response_db")


settings = Settings()
