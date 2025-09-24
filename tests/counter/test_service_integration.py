from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from src.domain.counter.service import CounterExhaustedError, CounterService
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


def make_service(repository, year: str = "54") -> tuple[CounterService, StubMetrics]:
    metrics = StubMetrics()
    provider = FixedAcademicYearProvider(year_code=year)
    service = CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt")
    return service, metrics


def test_generate_then_reuse(repository) -> None:
    service, metrics = make_service(repository)
    counter = service.get_or_create("1234567890", 1)

    reused = service.get_or_create("1234567890", 1)
    assert counter == reused
    assert metrics.generated[("54", 1)] == 1
    assert metrics.reuse[("54", 1)] == 1
    assert metrics.sequence_position[("54", "357")] >= 1


def test_reuse_across_year_warning(repository) -> None:
    service54, metrics = make_service(repository, year="54")
    generated = service54.get_or_create("0011223344", 0)

    service55, _ = make_service(repository, year="55")
    reused = service55.get_or_create("0011223344", 0)
    assert reused == generated


def test_parallel_generation_unique(repository) -> None:
    service, metrics = make_service(repository)

    national_ids = [f"00{i:08d}" for i in range(100)]

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda nid: service.get_or_create(nid, 1), national_ids))

    assert len(results) == len(set(results))
    assert all(result.startswith("54357") for result in results)


def test_bootstrap_sequence(repository) -> None:
    service, _ = make_service(repository)

    counter = service.get_or_create("1111111111", 0)
    assert counter.startswith("54373")


def test_overflow_triggers_error(repository, engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_sequences (year_code, prefix, next_seq, updated_at)
                VALUES ('54', '357', 10000, CURRENT_TIMESTAMP)
                ON CONFLICT(year_code, prefix) DO UPDATE SET next_seq=excluded.next_seq
                """
            )
        )
    service, _ = make_service(repository)

    with pytest.raises(CounterExhaustedError) as excinfo:
        service.get_or_create("2222222222", 1)
    assert excinfo.value.code == "E_COUNTER_EXHAUSTED"
