from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class Comment(BaseModel):
    id: Optional[int] = None
    response_id: UUID
    user_id: UUID
    content: str
    created_at: Optional[datetime] = datetime.now()
    updated_at: Optional[datetime] = datetime.now()


