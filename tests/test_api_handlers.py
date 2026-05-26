from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_comment_service
from src.api.handlers import router


def test_get_response_comments_returns_404_when_response_missing() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/response")

    comment_service = AsyncMock()
    comment_service.get_response_comments.return_value = None
    app.dependency_overrides[get_comment_service] = lambda: comment_service

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/response/responses/{uuid4()}/comments")

    assert response.status_code == 404
