from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

class ResponseStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Response(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    user_id: UUID
    user_name: str = ""
    text: str
    status: ResponseStatus = ResponseStatus.PENDING
    attached_files: List[UUID] = Field(default_factory=list)
    # Use naive UTC datetimes — DB columns are TIMESTAMP WITHOUT TIME ZONE.
    # asyncpg rejects timezone-aware datetimes for non-tz columns.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)