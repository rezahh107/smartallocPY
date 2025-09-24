"""Prometheus metrics adapter and exporter controls for counter service."""
from __future__ import annotations

import atexit
from threading import Lock, Thread
from typing import Optional, Tuple, Union, cast
from wsgiref.simple_server import WSGIServer

from prometheus_client import Counter, Gauge, start_http_server

from src.domain.counter.ports import CounterMetrics

_COUNTER_REUSE = Counter(
    "counter_reuse_total",
    "Number of times a prior counter was reused.",
    labelnames=("year", "gender"),
)
_COUNTER_GENERATED = Counter(
    "counter_generated_total",
    "Number of times a new counter was generated.",
    labelnames=("year", "gender"),
)
_COUNTER_CONFLICT = Counter(
    "counter_conflict_total",
    "Number of repository conflicts encountered.",
    labelnames=("type",),
)
_COUNTER_OVERFLOW = Counter(
    "counter_overflow_total",
    "Number of times the sequence overflowed.",
    labelnames=("year", "gender"),
)
_COUNTER_BACKFILL_MISMATCH = Counter(
    "counter_backfill_mismatch_total",
    "Number of ledger/mapping mismatches discovered by the backfill pipeline.",
    labelnames=("type",),
)
_COUNTER_LAST_SEQUENCE = Gauge(
    "counter_last_sequence_position",
    "Last successfully reserved sequence number per (year,prefix).",
    labelnames=("year", "prefix"),
)
_EXPORTER_HEALTH = Gauge(
    "counter_metrics_http_started",
    "Whether the Prometheus HTTP exporter has been started (1) or stopped (0).",
)

_ExporterReturn = Union[WSGIServer, Tuple[WSGIServer, Thread]]

_EXPORTER_LOCK = Lock()
_EXPORTER_SERVER: Optional[WSGIServer] = None
_EXPORTER_THREAD: Optional[Thread] = None
_EXPORTER_ADDRESS: Optional[tuple[str, int]] = None


def start_metrics_http_server(port: int, addr: str = "0.0.0.0") -> int:  # nosec B104
    """Start the Prometheus HTTP exporter if not already running.

    Args:
        port: Desired TCP port. ``0`` requests an ephemeral port for testing.
        addr: Interface address to bind to (defaults to ``0.0.0.0``).

    Returns:
        The actual port that the exporter is bound to.

    Raises:
        RuntimeError: If the exporter is already running on a different address
            or port than requested.
    """

    global _EXPORTER_SERVER, _EXPORTER_ADDRESS, _EXPORTER_THREAD
    with _EXPORTER_LOCK:
        if _EXPORTER_SERVER is not None:
            if _EXPORTER_ADDRESS is None:  # pragma: no cover - defensive guard
                raise RuntimeError("Exporter metadata missing while server running.")
            current_addr, current_port = _EXPORTER_ADDRESS
            requested_port = port if port != 0 else current_port
            if (addr, requested_port) != (current_addr, current_port):
                raise RuntimeError(  # pragma: no cover - guard against conflicting bind
                    "Prometheus exporter already running on a different address/port.")
            return current_port

        raw_server = cast(_ExporterReturn, start_http_server(port, addr=addr))
        httpd: WSGIServer
        thread: Thread | None = None
        if isinstance(raw_server, tuple):  # pragma: no cover - compatibility
            httpd, thread = raw_server
        else:  # pragma: no cover - compatibility with legacy prometheus_client
            httpd = raw_server
        actual_port = int(httpd.server_port)
        _EXPORTER_SERVER = httpd
        _EXPORTER_THREAD = thread
        _EXPORTER_ADDRESS = (addr, actual_port)
        _EXPORTER_HEALTH.set(1)
        return actual_port


def stop_metrics_http_server() -> None:
    """Stop the Prometheus HTTP exporter if it is running."""

    global _EXPORTER_SERVER, _EXPORTER_ADDRESS, _EXPORTER_THREAD
    with _EXPORTER_LOCK:
        if _EXPORTER_SERVER is None:
            return
        try:  # pragma: no branch - best effort shutdown
            _EXPORTER_SERVER.shutdown()
            _EXPORTER_SERVER.server_close()
            if _EXPORTER_THREAD is not None:
                _EXPORTER_THREAD.join(timeout=1)
        finally:
            _EXPORTER_SERVER = None
            _EXPORTER_ADDRESS = None
            _EXPORTER_THREAD = None
            _EXPORTER_HEALTH.set(0)


def get_metrics_http_port() -> Optional[int]:
    """Return the exporter port if running, otherwise ``None``."""

    with _EXPORTER_LOCK:
        if _EXPORTER_SERVER is None:
            return None
        return int(_EXPORTER_SERVER.server_port)


def _register_shutdown_hook() -> None:
    atexit.register(stop_metrics_http_server)


_register_shutdown_hook()


class PrometheusCounterMetrics(CounterMetrics):
    """Concrete implementation of :class:`CounterMetrics`."""

    def observe_reuse(self, *, year: str, gender: int) -> None:
        _COUNTER_REUSE.labels(year=year, gender=str(gender)).inc()

    def observe_generation(self, *, year: str, gender: int) -> None:
        _COUNTER_GENERATED.labels(year=year, gender=str(gender)).inc()

    def observe_conflict(self, *, conflict_type: str) -> None:
        _COUNTER_CONFLICT.labels(type=conflict_type).inc()

    def observe_overflow(self, *, year: str, gender: int) -> None:
        _COUNTER_OVERFLOW.labels(year=year, gender=str(gender)).inc()

    def observe_backfill_mismatch(self, *, mismatch_type: str) -> None:
        _COUNTER_BACKFILL_MISMATCH.labels(type=mismatch_type).inc()

    def record_sequence_position(self, *, year: str, prefix: str, sequence: int) -> None:
        _COUNTER_LAST_SEQUENCE.labels(year=year, prefix=prefix).set(sequence)
