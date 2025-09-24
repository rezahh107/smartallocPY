from __future__ import annotations

import json

from sqlalchemy import text

from src.domain.counter.service import CounterService
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


def _build_service(repository: PostgresCounterRepository) -> tuple[CounterService, StubMetrics]:
    metrics = StubMetrics()
    provider = FixedAcademicYearProvider(year_code="54")
    service = CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt")
    return service, metrics


def test_service_handles_counter_collision_metrics_and_logs(engine, caplog) -> None:
    repository = PostgresCounterRepository(engine=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code)
                VALUES ('1111111111', '543730001', '54')
                """
            )
        )
    service, metrics = _build_service(repository)

    caplog.set_level("INFO", logger="src.domain.counter.service")
    counter = service.get_or_create("2222222222", 0)

    assert counter == "543730001"
    assert metrics.generated[("54", 0)] == 1
    entries = list(repository.iter_ledger())
    assert len(entries) == 1
    assert entries[0].national_id == "1111111111"


class BlindReadRepository(PostgresCounterRepository):
    """Repository that simulates a race by skipping the initial read."""

    def get_prior_counter(self, national_id: str):  # type: ignore[override]
        return None


def test_service_handles_national_id_race(engine, caplog) -> None:
    repository = BlindReadRepository(engine=engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code)
                VALUES ('3333333333', '543730005', '54')
                """
            )
        )
    service, metrics = _build_service(repository)

    caplog.set_level("INFO", logger="src.domain.counter.service")
    counter = service.get_or_create("3333333333", 0)

    assert counter == "543730005"
    assert metrics.conflicts["ledger_race"] == 1
    events = [json.loads(record.message) for record in caplog.records if record.name == "src.domain.counter.service"]
    assert any(event.get("event") == "counter_race" for event in events)
