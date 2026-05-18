"""Optional admin API key for sensitive routes."""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


async def require_admin_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """When API_ADMIN_KEY is set, require matching X-API-Key header."""
    expected = (settings.API_ADMIN_KEY or "").strip()
    if not expected:
        return
    if (x_api_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
