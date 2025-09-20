"""API endpoint routers."""

from .allocation import router as allocation_router
from .health import router as health_router

__all__ = ["allocation_router", "health_router"]
