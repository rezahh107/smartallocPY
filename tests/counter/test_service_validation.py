from __future__ import annotations

import pytest

from src.domain.counter.service import CounterService, CounterValidationError
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


def build_service(repository) -> CounterService:
    provider = FixedAcademicYearProvider(year_code="54")
    return CounterService(repository=repository, year_provider=provider, metrics=StubMetrics(), pii_hash_salt="salt")


def test_invalid_national_id_message(repository) -> None:
    service = build_service(repository)
    with pytest.raises(CounterValidationError) as excinfo:
        service.get_or_create("abc", 0)
    assert excinfo.value.code == "E_INVALID_NID"


def test_invalid_gender_message(repository) -> None:
    service = build_service(repository)
    with pytest.raises(CounterValidationError) as excinfo:
        service.get_or_create("0012345678", 2)  # type: ignore[arg-type]
    assert excinfo.value.code == "E_INVALID_GENDER"


def test_invalid_year_code_from_provider(repository) -> None:
    class BadProvider:
        def current_year_code(self) -> str:
            return "abc"

    metrics = StubMetrics()
    service = CounterService(
        repository=repository,
        year_provider=BadProvider(),
        metrics=metrics,
        pii_hash_salt="salt",
    )
    with pytest.raises(CounterValidationError) as excinfo:
        service.get_or_create("0012345678", 0)
    assert excinfo.value.code == "E_YEAR_CODE_INVALID"
