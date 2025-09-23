"""Pytest configuration exposing shared fixtures for tests."""

from __future__ import annotations

from .utils.special_schools_testtools import special_schools_override  # noqa: F401

__all__ = ["special_schools_override"]
