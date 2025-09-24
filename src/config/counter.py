"""Configuration helpers for the counter service."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CounterConfig:
    """Runtime configuration for counter related services."""

    db_url: str
    pii_hash_salt: str
    metrics_port: int
    environment: str

    @classmethod
    def from_env(cls) -> "CounterConfig":
        db_url = os.getenv("DATABASE_URL") or os.getenv("COUNTER_DATABASE_URL")
        if not db_url:
            raise RuntimeError("DATABASE_URL یا COUNTER_DATABASE_URL تعریف نشده است.")
        pii_hash_salt = os.getenv("PII_HASH_SALT", "")
        if not pii_hash_salt:
            raise RuntimeError("PII_HASH_SALT برای هش‌کردن شناسه‌ها الزامی است.")
        metrics_port_raw = os.getenv("COUNTER_METRICS_PORT", "8000")
        try:
            metrics_port = int(metrics_port_raw)
        except ValueError as exc:  # pragma: no cover - defensive
            raise RuntimeError("COUNTER_METRICS_PORT باید یک عدد صحیح باشد.") from exc
        environment = os.getenv("COUNTER_ENV", "dev")
        if environment not in {"dev", "stage", "prod"}:
            raise RuntimeError("COUNTER_ENV باید یکی از dev/stage/prod باشد.")
        return cls(
            db_url=db_url,
            pii_hash_salt=pii_hash_salt,
            metrics_port=metrics_port,
            environment=environment,
        )
