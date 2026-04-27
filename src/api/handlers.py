from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.response import Response, ResponseUpdate, ResponseStatusUpdate
from app.schemas.comment import Comment, CommentCreate

router = APIRouter()

@router.get("/{id}")
async def get_response(id: int):
    """Получение отклика по ID"""
    return {"id": id, "message": "Get response"}

@router.put("/{id}")
async def update_response(id: int, response: ResponseUpdate):
    """Обновление отклика"""
    return {"id": id, "updated": True}

@router.put("/{id}/status")
async def update_response_status(id: int, status_update: ResponseStatusUpdate):
    """Обновление статуса отклика"""
    return {"id": id, "status": status_update.status}