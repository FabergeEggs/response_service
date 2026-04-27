from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response as FastAPIResponse  
from uuid import UUID
from typing import List
from src.api.dto import (
    CreateResponseRequest, UpdateResponseRequest, ChangeStatusRequest,
    CreateCommentRequest
)
from src.models.response import Response  # ← модель данных
from src.models.comment import Comment
from src.services.response_service import ResponseService
from src.services.comment_service import CommentService
from src.services.media_client import MediaServiceClient
from src.api.dependencies import get_response_service, get_comment_service, get_media_client

router = APIRouter()

@router.get("/responses", response_model=List[Response])
async def get_task_responses(
    task_id: UUID,
    service: ResponseService = Depends(get_response_service)
):
    return await service.get_task_responses(task_id)

@router.get("/responses/{response_id}", response_model=Response)
async def get_response(
    response_id: UUID,
    service: ResponseService = Depends(get_response_service)
):
    resp = await service.get_response(response_id)
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
    return resp

@router.post("/responses", response_model=Response, status_code=201)
async def add_response(
    data: CreateResponseRequest,
    service: ResponseService = Depends(get_response_service)
):
    new_response = Response(
        task_id=data.task_id,
        user_id=data.user_id,
        text=data.text,
        attached_files=data.attached_files or []
    )
    return await service.add_response(new_response)

@router.put("/responses/{response_id}", response_model=Response)
async def change_response(
    response_id: UUID,
    data: UpdateResponseRequest,
    service: ResponseService = Depends(get_response_service)
):
    updated = await service.change_response(response_id, data.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Response not found")
    return updated

@router.delete("/responses/{response_id}", status_code=204)
async def delete_response(
    response_id: UUID,
    service: ResponseService = Depends(get_response_service)
):
    deleted = await service.delete_response(response_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Response not found")
    return None

@router.patch("/responses/{response_id}/status", response_model=Response)
async def change_response_status(
    response_id: UUID,
    data: ChangeStatusRequest,
    service: ResponseService = Depends(get_response_service)
):
    updated = await service.change_response_status(response_id, data.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Response not found")
    return updated

@router.post("/responses/{response_id}/comments", response_model=Comment, status_code=201)
async def add_comment(
    response_id: UUID,
    data: CreateCommentRequest,
    service: CommentService = Depends(get_comment_service)
):
    comment = Comment(
        response_id=response_id,
        user_id=data.user_id,
        content=data.text
    )
    created = await service.add_comment(response_id, comment)
    if not created:
        raise HTTPException(status_code=404, detail="Response not found")
    return created

@router.get("/comments/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: UUID,
    service: CommentService = Depends(get_comment_service)
):
    comment = await service.get_comment(comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment

@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    service: CommentService = Depends(get_comment_service)
):
    deleted = await service.delete_comment(comment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    return None

@router.get("/responses/{response_id}/comments", response_model=List[Comment])
async def get_response_comments(
    response_id: UUID,
    service: CommentService = Depends(get_comment_service)
):
    return await service.get_response_comments(response_id)

@router.post("/responses/{response_id}/files", response_model=UUID, status_code=201)
async def add_attached_file(
    response_id: UUID,
    file: UploadFile = File(...),
    response_service: ResponseService = Depends(get_response_service),
    media_client: MediaServiceClient = Depends(get_media_client)
):
    resp = await response_service.get_response(response_id)
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")

    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_id = await media_client.add_attached_file(file.file, file.filename)

    new_files = resp.attached_files + [file_id]
    updated = await response_service.change_response(response_id, {"attached_files": new_files})
    if not updated:
        await media_client.delete_attached_file(file_id)
        raise HTTPException(status_code=500, detail="Failed to update response")
    return file_id

@router.get("/responses/{response_id}/files/{file_id}")
async def get_attached_file(
    response_id: UUID,
    file_id: UUID,
    response_service: ResponseService = Depends(get_response_service),
    media_client: MediaServiceClient = Depends(get_media_client)
):
    resp = await response_service.get_response(response_id)
    if not resp or file_id not in resp.attached_files:
        raise HTTPException(status_code=404, detail="File not found in this response")

    content = await media_client.get_attached_file(file_id)
    # Используем FastAPIResponse, а не модель Response
    return FastAPIResponse(content=content, media_type="application/octet-stream")

@router.delete("/responses/{response_id}/files/{file_id}", status_code=204)
async def delete_attached_file(
    response_id: UUID,
    file_id: UUID,
    response_service: ResponseService = Depends(get_response_service),
    media_client: MediaServiceClient = Depends(get_media_client)
):
    resp = await response_service.get_response(response_id)
    if not resp or file_id not in resp.attached_files:
        raise HTTPException(status_code=404, detail="File not found in this response")

    await media_client.delete_attached_file(file_id)

    new_files = [fid for fid in resp.attached_files if fid != file_id]
    updated = await response_service.change_response(response_id, {"attached_files": new_files})
    if not updated:
        # В идеале здесь тоже нужен откат, но для простоты логируем
        raise HTTPException(status_code=500, detail="Failed to update response after file deletion")
    return None