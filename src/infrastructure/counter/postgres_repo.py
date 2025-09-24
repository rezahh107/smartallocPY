"""SQLAlchemy 2.0 implementation of the counter repository."""
from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Callable, Iterable

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Insert

from src.domain.counter.ports import CounterRecord, CounterRepository
from src.domain.counter.service import CounterConflictError

metadata = MetaData()

counter_ledger = Table(
    "counter_ledger",
    metadata,
    Column("national_id", String(10), primary_key=True),
    Column("counter", String(9), nullable=False, unique=True),
    Column("year_code", String(2), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "length(national_id) = 10 AND national_id >= '0000000000' AND national_id <= '9999999999'",
        name="ck_counter_ledger_national_id",
    ),
    CheckConstraint(
        "length(counter) = 9 AND substr(counter,3,3) IN ('357','373')",
        name="ck_counter_format_prefix",
    ),
    CheckConstraint(
        "counter >= '000000000' AND counter <= '999999999'",
        name="ck_counter_digits",
    ),
)

counter_sequences = Table(
    "counter_sequences",
    metadata,
    Column("year_code", String(2), nullable=False),
    Column("prefix", String(3), nullable=False),
    Column("next_seq", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    UniqueConstraint("year_code", "prefix", name="pk_counter_sequences"),
    CheckConstraint("prefix IN ('357','373')", name="ck_counter_sequences_prefix"),
    CheckConstraint("next_seq BETWEEN 1 AND 10000", name="ck_counter_sequences_bounds"),
)


@dataclass
class PostgresCounterRepository(CounterRepository):
    """SQL-backed implementation of the counter repository."""

    engine: Engine
    session_factory: Callable[[], AbstractContextManager[None]] | None = None

    def get_prior_counter(self, national_id: str) -> CounterRecord | None:
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    counter_ledger.c.national_id,
                    counter_ledger.c.counter,
                    counter_ledger.c.year_code,
                    counter_ledger.c.created_at,
                ).where(counter_ledger.c.national_id == national_id)
            ).one_or_none()
            if row:
                return CounterRecord(
                    national_id=row.national_id,
                    counter=row.counter,
                    year_code=row.year_code,
                    created_at=row.created_at,
                )
            return None

    def reserve_next_sequence(self, year_code: str, prefix: str) -> int:
        with self.engine.begin() as conn:
            try:
                result = conn.execute(
                    text(
                        """
                        UPDATE counter_sequences
                           SET next_seq = next_seq + 1,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE year_code = :year_code AND prefix = :prefix
                     RETURNING next_seq - 1 AS allocated
                        """
                    ),
                    {"year_code": year_code, "prefix": prefix},
                ).first()
            except IntegrityError as exc:
                overflow = conn.execute(
                    select(counter_sequences.c.next_seq).where(
                        counter_sequences.c.year_code == year_code,
                        counter_sequences.c.prefix == prefix,
                    )
                ).one_or_none()
                if overflow and overflow.next_seq >= 10000:
                    return 10000
                raise CounterConflictError(
                    code="E_DB_CONFLICT",
                    message_fa="به‌روزرسانی توالی با خطا مواجه شد.",
                    details={"year_code": year_code, "prefix": prefix},
                ) from exc
            if result:
                return int(result.allocated)

            try:
                conn.execute(
                    text(
                        """
                        INSERT INTO counter_sequences (year_code, prefix, next_seq)
                        VALUES (:year_code, :prefix, 1)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"year_code": year_code, "prefix": prefix},
                )
            except IntegrityError as exc:  # pragma: no cover - best effort
                raise CounterConflictError(
                    code="E_DB_CONFLICT",
                    message_fa="ثبت توالی اولیه با خطا مواجه شد.",
                    details={"year_code": year_code, "prefix": prefix},
                ) from exc

            try:
                result = conn.execute(
                    text(
                        """
                        UPDATE counter_sequences
                           SET next_seq = next_seq + 1,
                               updated_at = CURRENT_TIMESTAMP
                         WHERE year_code = :year_code AND prefix = :prefix
                     RETURNING next_seq - 1 AS allocated
                        """
                    ),
                    {"year_code": year_code, "prefix": prefix},
                ).first()
            except IntegrityError as exc:
                overflow = conn.execute(
                    select(counter_sequences.c.next_seq).where(
                        counter_sequences.c.year_code == year_code,
                        counter_sequences.c.prefix == prefix,
                    )
                ).one_or_none()
                if overflow and overflow.next_seq >= 10000:
                    return 10000
                raise CounterConflictError(
                    code="E_DB_CONFLICT",
                    message_fa="به‌روزرسانی توالی با خطا مواجه شد.",
                    details={"year_code": year_code, "prefix": prefix},
                ) from exc
            if not result:
                raise CounterConflictError(
                    code="E_DB_CONFLICT",
                    message_fa="رزرو توالی ناموفق بود.",
                    details={"year_code": year_code, "prefix": prefix},
                )
            return int(result.allocated)

    def bind_ledger(self, record: CounterRecord) -> CounterRecord:
        insert_stmt: Insert = counter_ledger.insert().values(
            national_id=record.national_id,
            counter=record.counter,
            year_code=record.year_code,
        )
        with self.engine.begin() as conn:
            try:
                conn.execute(insert_stmt)
            except IntegrityError as exc:
                existing = conn.execute(
                    select(
                        counter_ledger.c.national_id,
                        counter_ledger.c.counter,
                        counter_ledger.c.year_code,
                        counter_ledger.c.created_at,
                    ).where(counter_ledger.c.national_id == record.national_id)
                ).one_or_none()
                if existing:
                    return CounterRecord(
                        national_id=existing.national_id,
                        counter=existing.counter,
                        year_code=existing.year_code,
                        created_at=existing.created_at,
                    )
                existing_by_counter = conn.execute(
                    select(
                        counter_ledger.c.national_id,
                        counter_ledger.c.counter,
                        counter_ledger.c.year_code,
                        counter_ledger.c.created_at,
                    ).where(counter_ledger.c.counter == record.counter)
                ).one_or_none()
                if existing_by_counter:
                    return CounterRecord(
                        national_id=existing_by_counter.national_id,
                        counter=existing_by_counter.counter,
                        year_code=existing_by_counter.year_code,
                        created_at=existing_by_counter.created_at,
                    )
                raise CounterConflictError(
                    code="E_DB_CONFLICT",
                    message_fa="اطلاعات دفترچه در وضعیت ناسازگار است.",
                    details={"national_id": record.national_id},
                ) from exc

            row = conn.execute(
                select(
                    counter_ledger.c.national_id,
                    counter_ledger.c.counter,
                    counter_ledger.c.year_code,
                    counter_ledger.c.created_at,
                ).where(counter_ledger.c.national_id == record.national_id)
            ).one()
            return CounterRecord(
                national_id=row.national_id,
                counter=row.counter,
                year_code=row.year_code,
                created_at=row.created_at,
            )

    def iter_ledger(self) -> Iterable[CounterRecord]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    counter_ledger.c.national_id,
                    counter_ledger.c.counter,
                    counter_ledger.c.year_code,
                    counter_ledger.c.created_at,
                )
            ).all()
        for row in rows:
            yield CounterRecord(
                national_id=row.national_id,
                counter=row.counter,
                year_code=row.year_code,
                created_at=row.created_at,
            )

    def get_sequence_positions(self) -> dict[tuple[str, str], int]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    counter_sequences.c.year_code,
                    counter_sequences.c.prefix,
                    counter_sequences.c.next_seq,
                )
            ).all()
        return {(row.year_code, row.prefix): int(row.next_seq) for row in rows}

    def upsert_sequence_position(self, *, year_code: str, prefix: str, next_seq: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO counter_sequences (year_code, prefix, next_seq, updated_at)
                    VALUES (:year_code, :prefix, :next_seq, CURRENT_TIMESTAMP)
                    ON CONFLICT(year_code, prefix)
                    DO UPDATE SET next_seq = EXCLUDED.next_seq,
                                  updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {"year_code": year_code, "prefix": prefix, "next_seq": next_seq},
            )
