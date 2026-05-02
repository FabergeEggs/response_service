from fastapi import Request

from src.services.comment_service import CommentService
from src.services.media_client_protocol import MediaClient
from src.services.response_service import ResponseService


def get_response_service(request: Request) -> ResponseService:
    return request.app.state.response_service


def get_comment_service(request: Request) -> CommentService:
    return request.app.state.comment_service


def get_media_client(request: Request) -> MediaClient:
    return request.app.state.media_client
