from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.domain.counter.ports import CounterRecord, COUNTER_PREFIX
from src.domain.counter.service import (
    CounterConflictError,
    CounterService,
    CounterValidationError,
)
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics


@dataclass
class StubRepository:
    sequence: int = 1
    prior: CounterRecord | None = None
    bind_behavior: str | None = None

    def get_prior_counter(self, national_id: str) -> CounterRecord | None:
        return self.prior

    def reserve_next_sequence(self, year_code: str, prefix: str) -> int:
        return self.sequence

    def bind_ledger(self, record: CounterRecord) -> CounterRecord:
        if self.bind_behavior == "conflict":
            raise CounterConflictError(
                code="E_DB_CONFLICT",
                message_fa="conflict",
                details={},
            )
        if self.bind_behavior == "service_error":
            raise CounterValidationError(
                code="E_INVALID_NID",
                message_fa="bad",
                details={},
            )
        return record

    def iter_ledger(self):  # pragma: no cover - not used in these tests
        return []

    def get_sequence_positions(self):  # pragma: no cover - not used here
        return {}

    def upsert_sequence_position(self, *, year_code: str, prefix: str, next_seq: int) -> None:  # pragma: no cover
        return None


def build_service(repo: StubRepository) -> CounterService:
    provider = FixedAcademicYearProvider(year_code="54")
    metrics = StubMetrics()
    return CounterService(repository=repo, year_provider=provider, metrics=metrics, pii_hash_salt="salt")


def test_sequence_underflow_raises_db_conflict() -> None:
    repo = StubRepository(sequence=0)
    service = build_service(repo)
    with pytest.raises(CounterConflictError) as excinfo:
        service.get_or_create("1234567890", 0)
    assert excinfo.value.code == "E_DB_CONFLICT"


def test_counter_pattern_invalid(monkeypatch) -> None:
    repo = StubRepository(sequence=1)
    service = build_service(repo)
    monkeypatch.setitem(COUNTER_PREFIX, 0, "abc")
    with pytest.raises(CounterValidationError) as excinfo:
        service.get_or_create("1234567890", 0)
    assert excinfo.value.code == "E_COUNTER_PATTERN_INVALID"


def test_bind_conflict_is_propagated() -> None:
    repo = StubRepository(sequence=1, bind_behavior="conflict")
    service = build_service(repo)
    with pytest.raises(CounterConflictError):
        service.get_or_create("1234567890", 0)


def test_bind_service_error_reraises() -> None:
    repo = StubRepository(sequence=1, bind_behavior="service_error")
    service = build_service(repo)
    with pytest.raises(CounterValidationError):
        service.get_or_create("1234567890", 0)
