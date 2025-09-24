"""CLI for running the counter backfill."""
from __future__ import annotations

import argparse
import csv
import io
import logging
from pathlib import Path
import sys
from typing import Iterator, Literal, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine

from src.config.counter import CounterConfig
from src.domain.counter.ports import COUNTER_PREFIX
from src.domain.counter.service import CounterService
from src.infrastructure.counter.backfill import BackfillInput, BackfillRunner, CSVReporter
from src.infrastructure.counter.metrics import (
    PrometheusCounterMetrics,
    start_metrics_http_server,
)
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider

logging.basicConfig(level=logging.INFO, format="%(message)s")


def load_inputs(path: Path) -> Iterator[BackfillInput]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            gender = row.get("gender")
            if gender is None:
                logging.warning("Skipping row with invalid gender: %s", row)
                continue
            try:
                gender_value = int(gender)
            except ValueError:
                logging.warning("Skipping row with invalid gender: %s", row)
                continue
            if gender_value not in COUNTER_PREFIX:
                logging.warning("Skipping row with invalid gender: %s", row)
                continue
            national_id = row.get("national_id")
            if not national_id:
                logging.warning("Skipping row without national_id: %s", row)
                continue
            typed_gender = cast(Literal[0, 1], gender_value)
            yield BackfillInput(national_id=national_id, gender=typed_gender)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill counters from gender dataset")
    parser.add_argument("input_csv", type=Path, help="CSV file with national_id,gender")
    parser.add_argument("year_code", help="Academic year code to use for new counters")
    parser.add_argument("--db-url", dest="db_url", default=None, help="Database URL override")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Perform dry-run without changes")
    parser.add_argument(
        "--report", dest="report_path", type=Path, default=Path("backfill_report.csv"), help="Output CSV report path"
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = CounterConfig.from_env()
    db_url = args.db_url or config.db_url
    engine = create_engine(db_url, future=True)

    repository = PostgresCounterRepository(engine=engine)
    provider = FixedAcademicYearProvider(year_code=args.year_code)
    metrics = PrometheusCounterMetrics()
    exporter_port = start_metrics_http_server(config.metrics_port)
    logging.info("Prometheus metrics exporter listening on port %s", exporter_port)
    service = CounterService(
        repository=repository,
        year_provider=provider,
        metrics=metrics,
        pii_hash_salt=config.pii_hash_salt,
    )

    buffer_reporter = CSVReporter(buffer=io.StringIO())
    runner = BackfillRunner(service=service, reporter=buffer_reporter, dry_run=args.dry_run)

    inputs = list(load_inputs(args.input_csv))
    summary = runner.run(inputs)

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(buffer_reporter.content, encoding="utf-8")
    logging.info(
        "Backfill summary: processed=%s created=%s reused=%s errors=%s sequence_updates=%s",
        summary.processed,
        summary.created,
        summary.reused,
        summary.errors,
        summary.sequence_updates,
    )

    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
