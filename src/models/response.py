from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, timezone
from enum import Enum
from typing import List

class ResponseStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Response(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={UUID: str, datetime: lambda v: v.isoformat()}
    )

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    user_id: UUID
    text: str
    status: ResponseStatus = ResponseStatus.PENDING
    attached_files: List[UUID] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
