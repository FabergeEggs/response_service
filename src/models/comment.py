from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

class Comment(BaseModel):
    id: Optional[UUID] = None
    response_id: UUID
    user_id: UUID
    user_name: str = ""
    content: str
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(UTC))


