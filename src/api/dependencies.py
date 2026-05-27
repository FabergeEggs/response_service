import base64
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from src.services.comment_service import CommentService
from src.services.media_client import MediaServiceClient
from src.services.response_service import ResponseService

logger = logging.getLogger(__name__)


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification (KrakenD has already verified it)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        # Restore base64 padding
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as exc:
        logger.debug("JWT payload decode failed: %s", exc)
        return {}


def get_response_service(request: Request) -> ResponseService:
    return request.app.state.response_service

def get_comment_service(request: Request) -> CommentService:
    return request.app.state.comment_service

def get_media_client(request: Request) -> MediaServiceClient:
    return request.app.state.media_client

async def get_current_user_id(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> UUID:
    """Extract user ID from X-User-Id header (injected by KrakenD) with fallback to JWT Bearer parsing.

    KrakenD propagates the JWT 'sub' claim as X-User-Id via propagate_claims.
    Fallback handles cases where claim injection is skipped (e.g. issuer config mismatch)
    but the Bearer token itself is present — same pattern as project_service.
    """
    user_id_str: Optional[str] = x_user_id

    if not user_id_str:
        # Fallback: parse JWT Bearer token directly (no signature verification — KrakenD already did it)
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            payload = _decode_jwt_payload(auth[7:])
            user_id_str = payload.get("sub")
            if user_id_str:
                logger.debug("X-User-Id resolved from JWT sub claim (fallback)")

    if not user_id_str:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")

    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")
