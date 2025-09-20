"""Database configuration helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .settings import get_settings


def get_engine(echo: bool = False) -> Engine:
    """Return an SQLAlchemy engine configured from application settings."""

    settings = get_settings()
    return create_engine(settings.database_url, echo=echo, future=True)
