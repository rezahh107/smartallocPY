"""CLI entry-point for assigning counters."""
from __future__ import annotations

import argparse
import logging
from sqlalchemy import create_engine

from src.api.counter_api import assign_counter
from src.config.counter import CounterConfig
from src.domain.counter.service import CounterService
from src.infrastructure.counter.metrics import (
    PrometheusCounterMetrics,
    start_metrics_http_server,
)
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider

logging.basicConfig(level=logging.INFO, format="%(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assign deterministic counters")
    parser.add_argument("national_id", help="National ID (10 digits)")
    parser.add_argument("gender", type=int, choices=[0, 1], help="Gender code (0=female, 1=male)")
    parser.add_argument("year_code", help="Academic year code (YY)")
    parser.add_argument("--db-url", dest="db_url", default=None, help="Database URL; overrides env configuration")
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

    response = assign_counter(
        service=service,
        national_id=args.national_id,
        gender=args.gender,
        year_code=args.year_code,
    )
    if response.ok:
        logging.info("%s", response.payload["counter"])
        return 0
    logging.error("%s", response.payload)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
