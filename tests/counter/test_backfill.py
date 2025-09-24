from __future__ import annotations

import io

from sqlalchemy import text

from src.infrastructure.counter.backfill import BackfillInput, BackfillRunner, CSVReporter
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider
from tests.counter.conftest import StubMetrics
from src.domain.counter.service import CounterService


def build_service(repository) -> tuple[CounterService, StubMetrics]:
    provider = FixedAcademicYearProvider(year_code="54")
    metrics = StubMetrics()
    return (
        CounterService(repository=repository, year_provider=provider, metrics=metrics, pii_hash_salt="salt"),
        metrics,
    )


def test_backfill_reports_gender_mismatch(repository, engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code, created_at)
                VALUES ('1234567890', '543570001', '54', CURRENT_TIMESTAMP)
                """
            )
        )
    service, metrics = build_service(repository)
    buffer = io.StringIO()
    reporter = CSVReporter(buffer=buffer)
    runner = BackfillRunner(service=service, reporter=reporter)

    summary = runner.run([BackfillInput(national_id="1234567890", gender=0)])

    assert summary.errors == 1
    assert "E_LEDGER_GENDER_MISMATCH" in reporter.content
    assert metrics.mismatches["gender_prefix"] == 1


def test_backfill_dry_run_no_changes(repository) -> None:
    service, _ = build_service(repository)
    buffer = io.StringIO()
    reporter = CSVReporter(buffer=buffer)
    runner = BackfillRunner(service=service, reporter=reporter, dry_run=True)

    summary = runner.run([BackfillInput(national_id="9999999999", gender=1)])

    assert summary.created == 0
    assert "DRY_RUN_MISSING" in reporter.content
    # No sequence rows should be created during dry-run reconciliation.
    with repository.engine.connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM counter_sequences")
        ).scalar_one()
    assert row == 0


def test_backfill_dry_run_sequence_report(repository, engine) -> None:
    service, _ = build_service(repository)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code, created_at)
                VALUES ('8888888888', '543730050', '54', CURRENT_TIMESTAMP)
                """
            )
        )
    buffer = io.StringIO()
    reporter = CSVReporter(buffer=buffer)
    runner = BackfillRunner(service=service, reporter=reporter, dry_run=True)

    summary = runner.run([])

    assert summary.sequence_updates == 1
    assert "SEQUENCE_UPDATE_DRY_RUN" in reporter.content


def test_backfill_derives_sequence(repository, engine) -> None:
    service, metrics = build_service(repository)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code, created_at)
                VALUES ('2222222222', '543730123', '54', CURRENT_TIMESTAMP)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO counter_sequences (year_code, prefix, next_seq, updated_at)
                VALUES ('54', '373', 5, CURRENT_TIMESTAMP)
                ON CONFLICT(year_code, prefix) DO NOTHING
                """
            )
        )
    buffer = io.StringIO()
    reporter = CSVReporter(buffer=buffer)
    runner = BackfillRunner(service=service, reporter=reporter, dry_run=False)

    summary = runner.run([])

    assert summary.sequence_updates == 1
    assert "SEQUENCE_UPDATE" in reporter.content
    with engine.connect() as conn:
        next_seq = conn.execute(
            text("SELECT next_seq FROM counter_sequences WHERE year_code='54' AND prefix='373'")
        ).scalar_one()
    assert next_seq == 124
    assert metrics.sequence_position[("54", "373")] == 123


def test_backfill_idempotent_run(repository, engine) -> None:
    service, _ = build_service(repository)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO counter_ledger (national_id, counter, year_code, created_at)
                VALUES ('3333333333', '543570010', '54', CURRENT_TIMESTAMP)
                """
            )
        )
    runner = BackfillRunner(service=service, reporter=None, dry_run=False)

    first = runner.run([])
    second = runner.run([])

    assert first.sequence_updates >= 1
    assert second.sequence_updates == 0


def test_backfill_no_ledger(repository) -> None:
    service, _ = build_service(repository)
    runner = BackfillRunner(service=service, reporter=None, dry_run=False)
    summary = runner.run([])
    assert summary.sequence_updates == 0


def test_backfill_handles_service_error(repository) -> None:
    service, _ = build_service(repository)
    buffer = io.StringIO()
    reporter = CSVReporter(buffer=buffer)
    runner = BackfillRunner(service=service, reporter=reporter, dry_run=False)

    summary = runner.run([BackfillInput(national_id="invalid", gender=0)])

    assert summary.errors == 1
    assert "E_INVALID_NID" in reporter.content
