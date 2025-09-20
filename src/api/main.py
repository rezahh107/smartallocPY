"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from ..config.settings import get_settings
from .endpoints import allocation, health


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health.router)
app.include_router(allocation.router)
