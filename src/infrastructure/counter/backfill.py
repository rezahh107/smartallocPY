"""Backfill tool for reconciling counter ledger with gender registry."""
from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from typing import Iterable, Literal, Sequence

from src.domain.counter.ports import BackfillReporter, COUNTER_PREFIX
from src.domain.counter.service import CounterService, CounterServiceError

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackfillInput:
    """Input row consumed by :class:`BackfillRunner`."""

    national_id: str
    gender: Literal[0, 1]


@dataclass
class BackfillSummary:
    """Aggregated results of a backfill run."""

    processed: int = 0
    created: int = 0
    reused: int = 0
    errors: int = 0
    error_codes: dict[str, int] = field(default_factory=dict)
    sequence_updates: int = 0

    def register_error(self, code: str) -> None:
        self.errors += 1
        self.error_codes[code] = self.error_codes.get(code, 0) + 1


class CSVReporter(BackfillReporter):
    """Reporter implementation writing rows into a CSV buffer."""

    def __init__(self, buffer: io.StringIO) -> None:
        self._buffer = buffer
        self._writer = csv.DictWriter(
            buffer,
            fieldnames=["national_id", "code", "message", "details"],
        )
        self._writer.writeheader()

    def emit_rows(self, rows: Iterable[dict[str, str]]) -> None:
        for row in rows:
            self._writer.writerow(row)

    @property
    def content(self) -> str:
        return self._buffer.getvalue()


class BackfillRunner:
    """High level orchestrator for backfill operations."""

    def __init__(
        self,
        service: CounterService,
        reporter: BackfillReporter | None = None,
        dry_run: bool = False,
    ) -> None:
        self._service = service
        self._reporter = reporter
        self._dry_run = dry_run

    def run(self, inputs: Sequence[BackfillInput]) -> BackfillSummary:
        summary = BackfillSummary()
        rows_to_report: list[dict[str, str]] = []
        for entry in inputs:
            summary.processed += 1
            try:
                result = self._service.repository.get_prior_counter(entry.national_id)
            except Exception as exc:  # pragma: no cover - guardrail
                LOGGER.error(
                    json.dumps(
                        {
                            "event": "backfill_lookup_failed",
                            "national_id": entry.national_id,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                    )
                )
                summary.register_error("E_DB_LOOKUP_FAILED")
                continue

            expected_prefix = COUNTER_PREFIX[entry.gender]
            if result:
                if result.counter[2:5] != expected_prefix:
                    rows_to_report.append(
                        {
                            "national_id": entry.national_id,
                            "code": "E_LEDGER_GENDER_MISMATCH",
                            "message": "پیشوند شماره با جنسیت منطبق نیست.",
                            "details": json.dumps(
                                {
                                    "counter": result.counter,
                                    "expected_prefix": expected_prefix,
                                },
                                ensure_ascii=False,
                            ),
                        }
                    )
                    summary.register_error("E_LEDGER_GENDER_MISMATCH")
                    self._service.metrics.observe_backfill_mismatch(
                        mismatch_type="gender_prefix"
                    )
                else:
                    summary.reused += 1
                continue

            if self._dry_run:
                rows_to_report.append(
                    {
                        "national_id": entry.national_id,
                        "code": "DRY_RUN_MISSING",
                        "message": "درای-ران: بدون ایجاد رکورد جدید.",
                        "details": json.dumps({"gender": str(entry.gender)}, ensure_ascii=False),
                    }
                )
                continue

            try:
                counter = self._service.get_or_create(entry.national_id, entry.gender)
                rows_to_report.append(
                    {
                        "national_id": entry.national_id,
                        "code": "ASSIGNED",
                        "message": "شناسه جدید تخصیص داده شد.",
                        "details": json.dumps({"counter": counter}, ensure_ascii=False),
                    }
                )
                summary.created += 1
            except CounterServiceError as exc:
                rows_to_report.append(
                    {
                        "national_id": entry.national_id,
                        "code": exc.code,
                        "message": exc.message_fa,
                        "details": json.dumps(exc.details or {}, ensure_ascii=False),
                    }
                )
                summary.register_error(exc.code)

        rows_to_report.extend(self._reconcile_sequences(summary))
        if self._reporter:
            self._reporter.emit_rows(rows_to_report)
        return summary

    def _reconcile_sequences(self, summary: BackfillSummary) -> list[dict[str, str]]:
        """Ensure ``counter_sequences`` aligns with ledger derived maxima."""

        rows: list[dict[str, str]] = []
        ledger_max: dict[tuple[str, str], int] = {}
        for record in self._service.repository.iter_ledger():
            prefix = record.counter[2:5]
            sequence = int(record.counter[5:])
            key = (record.year_code, prefix)
            ledger_max[key] = max(ledger_max.get(key, 0), sequence)

        if not ledger_max:
            return rows

        sequence_positions = self._service.repository.get_sequence_positions()
        for (year_code, prefix), max_sequence in ledger_max.items():
            expected_next = max_sequence + 1
            current = sequence_positions.get((year_code, prefix))
            if current == expected_next:
                continue

            summary.sequence_updates += 1
            details_payload = {
                "year_code": year_code,
                "prefix": prefix,
                "current_next_seq": current,
                "expected_next_seq": expected_next,
            }
            details = json.dumps(details_payload, ensure_ascii=False)

            if self._dry_run:
                rows.append(
                    {
                        "national_id": f"{year_code}-{prefix}",
                        "code": "SEQUENCE_UPDATE_DRY_RUN",
                        "message": "درای-ران: بروزرسانی توالی لازم است.",
                        "details": details,
                    }
                )
                continue

            self._service.repository.upsert_sequence_position(
                year_code=year_code,
                prefix=prefix,
                next_seq=expected_next,
            )
            self._service.metrics.record_sequence_position(
                year=year_code,
                prefix=prefix,
                sequence=max_sequence,
            )
            rows.append(
                {
                    "national_id": f"{year_code}-{prefix}",
                    "code": "SEQUENCE_UPDATE",
                    "message": "توالی به مقدار صحیح به‌روزرسانی شد.",
                    "details": details,
                }
            )
        return rows
