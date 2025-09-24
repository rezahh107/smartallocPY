from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from concurrent.futures import ThreadPoolExecutor

from src.api.counter_api import assign_counter
from src.domain.counter.service import CounterService
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


def build_service(repository) -> CounterService:
    provider = FixedAcademicYearProvider(year_code="54")
    return CounterService(repository=repository, year_provider=provider, metrics=StubMetrics(), pii_hash_salt="salt")


def test_assign_counter_ok(repository) -> None:
    service = build_service(repository)
    response = assign_counter(service=service, national_id="1234567890", gender=0, year_code="54")
    assert response.ok
    assert response.payload["counter"].startswith("54373")


def test_assign_counter_error_payload(repository) -> None:
    service = build_service(repository)
    response = assign_counter(service=service, national_id="bad", gender=0, year_code="54")
    assert not response.ok
    assert response.payload["code"] == "E_INVALID_NID"
    assert "message_fa" in response.payload


def test_assign_counter_year_mismatch(repository) -> None:
    service = build_service(repository)
    response = assign_counter(service=service, national_id="1234567890", gender=0, year_code="55")
    assert not response.ok
    assert response.payload["code"] == "E_YEAR_CODE_INVALID"


def test_assign_counter_invalid_year_format(repository) -> None:
    service = build_service(repository)
    response = assign_counter(service=service, national_id="1234567890", gender=0, year_code="abc")
    assert not response.ok
    assert response.payload["code"] == "E_YEAR_CODE_INVALID"


def test_parallel_calls_single_assignment(repository) -> None:
    service = build_service(repository)

    def call() -> str:
        resp = assign_counter(service=service, national_id="1111111111", gender=1, year_code="54")
        assert resp.ok
        return resp.payload["counter"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: call(), range(2)))

    assert results[0] == results[1]
