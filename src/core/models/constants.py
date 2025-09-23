"""Shared constant sets for student and mentor domain models."""

from __future__ import annotations

from typing import FrozenSet

GENDER_CODES: FrozenSet[int] = frozenset({0, 1})
"""Valid gender codes accepted by the allocation system."""

EDU_STATUS_CODES: FrozenSet[int] = frozenset({0, 1})
"""Educational status codes: 0 for graduate, 1 for active student."""

REG_CENTER_CODES: FrozenSet[int] = frozenset({0, 1, 2})
"""Registration center codes representing allowable physical centers."""

REG_STATUS_CODES: FrozenSet[int] = frozenset({0, 1, 3})
"""Registration status codes approved for allocation workflows."""

DEFAULT_SPECIAL_SCHOOLS: FrozenSet[int] = frozenset({283, 650})
"""Initial set of special-school codes prior to seasonal configuration."""

__all__ = [
    "DEFAULT_SPECIAL_SCHOOLS",
    "EDU_STATUS_CODES",
    "GENDER_CODES",
    "REG_CENTER_CODES",
    "REG_STATUS_CODES",
]
