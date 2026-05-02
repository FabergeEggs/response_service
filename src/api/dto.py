from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from src.models.response import ResponseStatus

class CreateResponseRequest(BaseModel):
    task_id: UUID
    user_id: UUID
    text: str
    attached_files: Optional[List[UUID]] = []

class UpdateResponseRequest(BaseModel):
    text: Optional[str] = None
    status: Optional[ResponseStatus] = None
    attached_files: Optional[List[UUID]] = None

class ChangeStatusRequest(BaseModel):
    status: ResponseStatus

class CreateCommentRequest(BaseModel):
    user_id: UUID
    text: str
