from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.counter.ports import CounterMetrics
from src.domain.counter.service import CounterService
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository, metadata
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider


class StubMetrics(CounterMetrics):
    def __init__(self) -> None:
        self.reuse = defaultdict(int)
        self.generated = defaultdict(int)
        self.conflicts = defaultdict(int)
        self.overflow = defaultdict(int)
        self.mismatches = defaultdict(int)
        self.sequence_position = {}

    def observe_reuse(self, *, year: str, gender: int) -> None:
        self.reuse[(year, gender)] += 1

    def observe_generation(self, *, year: str, gender: int) -> None:
        self.generated[(year, gender)] += 1

    def observe_conflict(self, *, conflict_type: str) -> None:
        self.conflicts[conflict_type] += 1

    def observe_overflow(self, *, year: str, gender: int) -> None:
        self.overflow[(year, gender)] += 1

    def observe_backfill_mismatch(self, *, mismatch_type: str) -> None:
        self.mismatches[mismatch_type] += 1

    def record_sequence_position(self, *, year: str, prefix: str, sequence: int) -> None:
        self.sequence_position[(year, prefix)] = sequence


@pytest.fixture()
def engine(tmp_path) -> Engine:
    db_path = tmp_path / "counter.sqlite"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> PostgresCounterRepository:
    return PostgresCounterRepository(engine=engine)


@pytest.fixture()
def service(repository: PostgresCounterRepository) -> CounterService:
    metrics = StubMetrics()
    provider = FixedAcademicYearProvider(year_code="54")
    return CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt")
