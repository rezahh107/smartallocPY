"""Health check endpoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check() -> dict[str, str]:
    """Return a basic health payload."""

    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
