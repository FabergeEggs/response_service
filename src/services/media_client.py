from uuid import UUID
from typing import BinaryIO
import httpx
from src.core.config import settings

class MediaServiceClient:
    def __init__(self, base_url: str = settings.MEDIA_SERVICE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def add_attached_file(self, file: BinaryIO, filename: str) -> UUID:
        files = {"file": (filename, file, "application/octet-stream")}
        resp = await self.client.post(f"{self.base_url}/attached_files", files=files)
        resp.raise_for_status()
        return UUID(resp.json()["file_id"])

    async def delete_attached_file(self, file_id: UUID) -> bool:
        resp = await self.client.delete(f"{self.base_url}/attached_files/{file_id}")
        resp.raise_for_status()
        return True

    async def get_attached_file(self, file_id: UUID) -> bytes:
        resp = await self.client.get(f"{self.base_url}/attached_files/{file_id}")
        resp.raise_for_status()
        return resp.content

    async def close(self):
        await self.client.aclose()
