from __future__ import annotations

from src.domain.counter.service import CounterService
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


def test_get_or_create_idempotent(repository) -> None:
    provider = FixedAcademicYearProvider(year_code="54")
    metrics = StubMetrics()
    service = CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt")

    counter1 = service.get_or_create("0012345678", 0)
    counter2 = service.get_or_create("0012345678", 0)

    assert counter1 == counter2
    assert metrics.generated[("54", 0)] == 1
    assert metrics.reuse[("54", 0)] == 1


def test_log_event_supplies_correlation_id(repository, caplog) -> None:
    provider = FixedAcademicYearProvider(year_code="54")
    metrics = StubMetrics()
    service = CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt")
    with caplog.at_level("INFO"):
        service._log_event("manual_event")
    assert "manual_event" in caplog.text
