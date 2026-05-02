import logging
from typing import BinaryIO
from uuid import UUID

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class MediaServiceClient:
    """Реализует протокол MediaClient."""

    def __init__(self, base_url: str = settings.MEDIA_SERVICE_URL) -> None:
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)

    async def add_attached_file(self, file: BinaryIO, filename: str) -> UUID:
        files = {"file": (filename, file, "application/octet-stream")}
        try:
            resp = await self._client.post(f"{self.base_url}/attached_files", files=files)
            resp.raise_for_status()
            return UUID(resp.json()["file_id"])
        except httpx.HTTPStatusError as e:
            logger.error("Media service returned error: %s %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("Failed to connect to media service: %s", e)
            raise
        except (KeyError, ValueError) as e:
            logger.error("Invalid response from media service: %s", e)
            raise

    async def get_attached_file(self, file_id: UUID) -> bytes:
        try:
            resp = await self._client.get(f"{self.base_url}/attached_files/{file_id}")
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as e:
            logger.error("Media service returned error: %s %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("Failed to connect to media service: %s", e)
            raise

    async def delete_attached_file(self, file_id: UUID) -> bool:
        try:
            resp = await self._client.delete(f"{self.base_url}/attached_files/{file_id}")
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error("Media service returned error: %s %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("Failed to connect to media service: %s", e)
            raise

    async def close(self) -> None:
        await self._client.aclose()
