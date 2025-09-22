from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

import pytest


@dataclass
class StudentStub:
    """Minimal student stand-in for mentor acceptance checks."""

    gender: int = 0
    edu_status: int = 1
    student_type: int = 0
    group_code: int = 10
    school_code: int | None = None


@pytest.fixture(autouse=True)
def seed_random() -> None:
    """Ensure deterministic behaviour for tests relying on randomness."""

    random.seed(1337)


@pytest.fixture
def student_factory() -> Callable[..., StudentStub]:
    """Return a factory for creating ``StudentStub`` instances."""

    def _factory(**overrides: object) -> StudentStub:
        data: dict[str, object] = {
            "gender": 0,
            "edu_status": 1,
            "student_type": 0,
            "group_code": 10,
            "school_code": None,
        }
        data.update(overrides)
        return StudentStub(**data)

    return _factory


def valid_national_id(prefix: str = "123456789") -> str:
    """Return a valid national ID using the Iranian mod-11 checksum."""

    if len(prefix) != 9 or not prefix.isdigit():
        raise ValueError("prefix must be a nine-digit string")
    digits = [int(char) for char in prefix]
    total = sum(digits[index] * (10 - index) for index in range(9))
    remainder = total % 11
    checksum = remainder if remainder < 2 else 11 - remainder
    return f"{prefix}{checksum}"


__all__ = ["StudentStub", "student_factory", "seed_random", "valid_national_id"]


def pytest_configure(config: pytest.Config) -> None:
    """Normalize coverage source paths for pytest-cov."""

    cov_source = getattr(config.option, "cov_source", None)
    if not cov_source:
        return
    normalized: list[str] = []
    for entry in cov_source:
        if entry == "src/core/models/mentor.py":
            continue
        normalized.append(entry)
    if "src.core.models.mentor" not in normalized:
        normalized.append("src.core.models.mentor")
    config.option.cov_source = normalized
