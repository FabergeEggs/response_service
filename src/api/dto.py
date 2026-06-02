from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from src.models.response import ResponseStatus

class CreateResponseRequest(BaseModel):
    task_id: UUID
    # user_id is injected from X-User-Id header by the API gateway (not from request body)
    text: str
    attached_files: Optional[List[str]] = []

class CreateResponseForTaskRequest(BaseModel):
    """Used by path-based endpoint POST /tasks/{task_id}/responses.
    task_id comes from the URL path, not the request body.
    user_id comes from X-User-Id header injected by the API gateway.
    """
    text: str
    attached_files: Optional[List[str]] = []

class UpdateResponseRequest(BaseModel):
    text: Optional[str] = None
    status: Optional[ResponseStatus] = None
    attached_files: Optional[List[str]] = None

class ChangeStatusRequest(BaseModel):
    status: ResponseStatus

class CreateCommentRequest(BaseModel):
    # user_id is injected from X-User-Id header by the API gateway (not from request body)
    text: str
