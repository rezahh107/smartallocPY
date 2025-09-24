"""Domain ports and constants for counter service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol

COUNTER_PREFIX: dict[int, str] = {0: "373", 1: "357"}
"""Single source of truth mapping for gender→counter prefix."""

GENDER_ALIASES: dict[str, int] = {
    "0": 0,
    "1": 1,
    "f": 0,
    "female": 0,
    "زن": 0,
    "ز": 0,
    "m": 1,
    "male": 1,
    "مرد": 1,
    "م": 1,
}
"""Aliases for upstream ingestion; the service still consumes Literal[0,1]."""


@dataclass(frozen=True)
class CounterRecord:
    """Immutable view of a stored counter assignment."""

    national_id: str
    counter: str
    year_code: str
    created_at: datetime | None


class CounterRepository(Protocol):
    """Port describing persistence operations for counters."""

    def get_prior_counter(self, national_id: str) -> CounterRecord | None:
        """Return an existing counter for ``national_id`` if present."""

    def reserve_next_sequence(self, year_code: str, prefix: str) -> int:
        """Atomically reserve the next sequence number for the given key."""

    def bind_ledger(self, record: CounterRecord) -> CounterRecord:
        """Persist the record in the ledger, returning the stored value."""

    def iter_ledger(self) -> Iterable[CounterRecord]:
        """Yield all ledger records for auditing/backfill purposes."""

    def get_sequence_positions(self) -> dict[tuple[str, str], int]:
        """Return the current ``next_seq`` values keyed by ``(year_code, prefix)``."""

    def upsert_sequence_position(self, *, year_code: str, prefix: str, next_seq: int) -> None:
        """Ensure ``counter_sequences`` holds ``next_seq`` for the key (idempotent)."""


class AcademicYearProvider(Protocol):
    """Port describing how the academic year code is sourced."""

    def current_year_code(self) -> str:
        """Return the two-digit academic year code (``YY``)."""


class CounterMetrics(Protocol):
    """Port for emitting counter-related metrics."""

    def observe_reuse(self, *, year: str, gender: int) -> None:
        """Increment reuse metric."""

    def observe_generation(self, *, year: str, gender: int) -> None:
        """Increment generation metric."""

    def observe_conflict(self, *, conflict_type: str) -> None:
        """Increment conflict metric by type."""

    def observe_overflow(self, *, year: str, gender: int) -> None:
        """Increment overflow metric."""

    def observe_backfill_mismatch(self, *, mismatch_type: str) -> None:
        """Increment mismatch metric emitted by the backfill pipeline."""

    def record_sequence_position(self, *, year: str, prefix: str, sequence: int) -> None:
        """Record the most recent reserved sequence position as a gauge."""


class BackfillReporter(Protocol):
    """Port for producing structured reports out of the backfill tool."""

    def emit_rows(self, rows: Iterable[dict[str, str]]) -> None:
        """Persist a sequence of report rows (e.g., CSV writer)."""
