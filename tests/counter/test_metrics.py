from __future__ import annotations

import time
import urllib.request

import pytest

from src.infrastructure.counter.metrics import (
    PrometheusCounterMetrics,
    get_metrics_http_port,
    start_metrics_http_server,
    stop_metrics_http_server,
)


@pytest.fixture(autouse=True)
def cleanup_exporter() -> None:
    """Ensure the Prometheus exporter is torn down between tests."""

    yield
    stop_metrics_http_server()


def test_prometheus_metrics_expose_all_methods() -> None:
    metrics = PrometheusCounterMetrics()
    metrics.observe_reuse(year="54", gender=0)
    metrics.observe_generation(year="54", gender=1)
    metrics.observe_conflict(conflict_type="ledger_conflict")
    metrics.observe_overflow(year="54", gender=1)
    metrics.observe_backfill_mismatch(mismatch_type="gender_prefix")
    metrics.record_sequence_position(year="54", prefix="373", sequence=42)


def test_metrics_exporter_start_once_and_scrape() -> None:
    port = start_metrics_http_server(0)
    metrics = PrometheusCounterMetrics()
    metrics.observe_generation(year="54", gender=1)

    # Allow the background server thread to boot before scraping.
    for _ in range(10):
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=1)
            break
        except Exception:  # pragma: no cover - retry loop
            time.sleep(0.05)
    else:  # pragma: no cover - diagnostic
        pytest.fail("Prometheus exporter did not start in time")

    body = response.read().decode("utf-8")
    assert "counter_generated_total" in body
    assert "counter_metrics_http_started 1.0" in body

    # Repeated start on the same port is a no-op and returns the current port.
    same_port = start_metrics_http_server(port)
    assert same_port == port
    assert get_metrics_http_port() == port
    stop_metrics_http_server()
    assert get_metrics_http_port() is None
