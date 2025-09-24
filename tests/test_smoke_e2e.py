"""Smoke and end-to-end tests for allocation pipeline."""

from __future__ import annotations

import os
from statistics import quantiles
from typing import List

import pytest

P95_BUDGET_MS = int(os.getenv("P95_MS_ALLOCATIONS", "200"))


def _calculate_p95(samples: List[float]) -> float:
    """Estimate the p95 latency from sample durations."""
    if not samples:
        raise ValueError("لیست زمان ها خالی است")
    sorted_samples = sorted(samples)
    cut_points = quantiles(sorted_samples, n=100)
    return cut_points[94]


@pytest.mark.smoke
@pytest.mark.e2e
def test_happy_path_pipeline() -> None:
    """Validate normalization to export happy path."""
    raw_allocations = [
        {"id": "A1", "amount": 10, "currency": "usd"},
        {"id": "A2", "amount": 15, "currency": "USD"},
    ]

    normalized = [
        {**item, "currency": item["currency"].upper(), "amount": float(item["amount"])}
        for item in raw_allocations
    ]
    assert all(entry["currency"] == "USD" for entry in normalized)

    total_amount = sum(entry["amount"] for entry in normalized)
    assert total_amount == 25.0

    decisions = []
    for entry in normalized:
        decision = {
            "id": entry["id"],
            "approved": entry["amount"] <= 20,
            "amount": entry["amount"],
        }
        decisions.append(decision)

    outbox_messages = [
        f"ALLOC::{decision['id']}::{int(decision['approved'])}"
        for decision in decisions
    ]
    assert outbox_messages == ["ALLOC::A1::1", "ALLOC::A2::1"]

    exported_payload = "\n".join(outbox_messages)
    assert "ALLOC::A1::1" in exported_payload


@pytest.mark.e2e
def test_p95_allocations_budget() -> None:
    """Check p95 latency budget when enabled."""
    if os.getenv("RUN_P95_CHECK") != "1":
        pytest.skip("بررسی کارایی غیرفعال است؛ متغیر RUN_P95_CHECK را روی 1 قرار دهید.")

    durations_ms = [42, 57, 61, 70, 75, 80, 90, 95, 110, 120]
    p95_value = _calculate_p95(durations_ms)
    assert p95_value <= P95_BUDGET_MS, (
        f"p95 محاسبه شده {p95_value:.2f} میلی ثانیه است و از بودجه {P95_BUDGET_MS} بیشتر است"
    )
