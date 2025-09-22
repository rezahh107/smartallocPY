from __future__ import annotations

from src.core.services.counter_service import CounterService


def test_counter_service_generates_unique_identifiers() -> None:
    service = CounterService(prefix="T-", start=5)

    first = service.next()
    second = service.next()
    third = service.next()

    assert first == "T-5"
    assert second == "T-6"
    assert third == "T-7"
    assert len({first, second, third}) == 3
