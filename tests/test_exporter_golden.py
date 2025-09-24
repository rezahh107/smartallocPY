"""Golden tests ensuring exporter determinism."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _paired_csvs(directory: Path) -> Dict[Path, Path]:
    """Map expected CSV files to their produced counterparts."""
    pairs: Dict[Path, Path] = {}
    for expected_file in directory.glob("*_expected.csv"):
        produced_file = expected_file.with_name(
            expected_file.name.replace("_expected.csv", "_produced.csv")
        )
        pairs[expected_file] = produced_file
    return pairs


@pytest.mark.golden
def test_exporter_matches_golden_snapshots() -> None:
    """Compare golden CSV snapshots byte-for-byte."""
    pairs = _paired_csvs(GOLDEN_DIR)
    if not pairs:
        pytest.xfail(
            "هیچ فایل طلایی ثبت نشده است؛ لطفاً فایل های *_expected.csv را اضافه کنید."
        )

    mismatches = []
    for expected_file, produced_file in pairs.items():
        if not produced_file.exists():
            pytest.fail(f"خروجی تولید شده یافت نشد: {produced_file}")
        expected_bytes = expected_file.read_bytes()
        produced_bytes = produced_file.read_bytes()
        if expected_bytes != produced_bytes:
            mismatches.append(
                f"عدم تطابق: {expected_file.name} با {produced_file.name}"
            )

    if mismatches:
        joined = "\n".join(mismatches)
        pytest.fail("پرونده های زیر با نمونه طلایی مطابقت ندارند:\n" + joined)
