from __future__ import annotations

from sqlalchemy import text

from src.domain.counter.ports import CounterRecord
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository


def test_bind_ledger_returns_existing_on_duplicate(repository: PostgresCounterRepository) -> None:
    record = CounterRecord(national_id="4444444444", counter="543730001", year_code="54", created_at=None)
    stored = repository.bind_ledger(record)
    assert stored.counter == "543730001"
    duplicate = repository.bind_ledger(record)
    assert duplicate.counter == "543730001"
    assert duplicate.national_id == "4444444444"


def test_bind_ledger_resolves_counter_collision(repository: PostgresCounterRepository, engine) -> None:
    record1 = CounterRecord(national_id="5555555555", counter="543730002", year_code="54", created_at=None)
    record2 = CounterRecord(national_id="6666666666", counter="543730002", year_code="54", created_at=None)
    repository.bind_ledger(record1)
    resolved = repository.bind_ledger(record2)
    assert resolved.national_id == "5555555555"


def test_repository_iterators(repository: PostgresCounterRepository, engine) -> None:
    repository.bind_ledger(CounterRecord(national_id="7777777777", counter="543730003", year_code="54", created_at=None))
    entries = list(repository.iter_ledger())
    assert any(entry.national_id == "7777777777" for entry in entries)
    positions = repository.get_sequence_positions()
    assert isinstance(positions, dict)
    repository.upsert_sequence_position(year_code="54", prefix="373", next_seq=10)
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT next_seq FROM counter_sequences WHERE year_code='54' AND prefix='373'")
        ).scalar_one()
    assert value == 10
