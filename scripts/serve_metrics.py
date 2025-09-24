"""Launch a long-lived Prometheus exporter for local operations."""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.counter.metrics import start_metrics_http_server


def main() -> int:
    port = int(os.getenv("COUNTER_METRICS_PORT", "8000"))
    actual = start_metrics_http_server(port)
    print(f"Prometheus exporter ready on http://0.0.0.0:{actual}/metrics")
    try:
        signal.pause()
    except (KeyboardInterrupt, SystemExit):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
