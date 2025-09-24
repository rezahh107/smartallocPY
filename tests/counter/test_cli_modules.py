from __future__ import annotations

import sys
import sys
import time
import urllib.request

from sqlalchemy import create_engine

from assign_counter import build_parser as assign_parser
from assign_counter import main as assign_main
from scripts.backfill_counters import build_parser as backfill_parser
from src.infrastructure.counter.metrics import get_metrics_http_port, stop_metrics_http_server
from src.infrastructure.counter.postgres_repo import metadata


def test_assign_parser_options() -> None:
    parser = assign_parser()
    args = parser.parse_args(["1234567890", "1", "54"])
    assert args.national_id == "1234567890"
    assert args.gender == 1
    assert args.year_code == "54"


def test_backfill_parser_flags(tmp_path) -> None:
    parser = backfill_parser()
    csv_path = tmp_path / "input.csv"
    csv_path.write_text("national_id,gender\n1234567890,1\n", encoding="utf-8")
    args = parser.parse_args([str(csv_path), "54", "--dry-run"])
    assert args.dry_run is True
    assert args.year_code == "54"


def _scrape_metrics(port: int) -> str:
    for _ in range(10):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=1) as response:
                return response.read().decode("utf-8")
        except Exception:  # pragma: no cover - retry loop
            time.sleep(0.05)
    raise AssertionError("metrics endpoint did not become ready in time")


def test_assign_main_starts_metrics_exporter(tmp_path, monkeypatch, caplog) -> None:
    db_path = tmp_path / "cli.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    metadata.create_all(engine)
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("PII_HASH_SALT", "salt")
    monkeypatch.setenv("COUNTER_ENV", "dev")
    monkeypatch.setenv("COUNTER_METRICS_PORT", "0")

    caplog.set_level("INFO")
    monkeypatch.setattr(sys, "argv", ["assign_counter.py", "1234567890", "1", "54"])
    exit_code = assign_main()
    assert exit_code == 0
    assert "Prometheus metrics exporter listening" in caplog.text

    port = get_metrics_http_port()
    assert port is not None and port > 0
    body = _scrape_metrics(port)
    assert "counter_generated_total" in body

    # Run again with the same national_id to exercise reuse path and exporter guard.
    monkeypatch.setenv("COUNTER_METRICS_PORT", str(port))
    monkeypatch.setattr(sys, "argv", ["assign_counter.py", "1234567890", "1", "54"])
    caplog.clear()
    assert assign_main() == 0
    body = _scrape_metrics(port)
    assert "counter_reuse_total" in body

    stop_metrics_http_server()
