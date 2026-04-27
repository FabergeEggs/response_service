from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import List, Optional

class ResponseStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Response(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    user_id: UUID
    text: str
    status: ResponseStatus = ResponseStatus.PENDING
    attached_files: List[UUID] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        json_encoders = {UUID: str, datetime: lambda v: v.isoformat()}