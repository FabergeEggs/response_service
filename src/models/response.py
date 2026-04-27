from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Response(BaseModel):
    id: Optional[int] = None
    task_id: int
    user_id: int
    content: str
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ResponseStatusUpdate(BaseModel):
    status: str