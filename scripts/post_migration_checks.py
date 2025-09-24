"""Run post-migration validation checks for counter tables."""
from __future__ import annotations

import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config.counter import CounterConfig
from src.infrastructure.counter.postgres_repo import counter_ledger, counter_sequences

logging.basicConfig(level=logging.INFO, format="%(message)s")

COUNTER_PATTERN = re.compile(r"^\d{2}(357|373)\d{4}$")
NATIONAL_ID_PATTERN = re.compile(r"^\d{10}$")


def _collect_sequence_mismatches(ledger_rows: Iterable[tuple[str, str]]) -> dict[tuple[str, str], int]:
    derived: dict[tuple[str, str], int] = {}
    for counter, year_code in ledger_rows:
        prefix = counter[2:5]
        sequence = int(counter[-4:])
        key = (year_code, prefix)
        current = derived.get(key, 0)
        derived[key] = max(current, sequence)
    return derived


def main() -> int:
    config = CounterConfig.from_env()
    engine = create_engine(config.db_url, future=True)

    failures: list[str] = []
    with engine.connect() as conn:
        ledger_data = conn.execute(
            select(
                counter_ledger.c.national_id,
                counter_ledger.c.counter,
                counter_ledger.c.year_code,
            )
        ).all()

        invalid_counters = [row.counter for row in ledger_data if not COUNTER_PATTERN.fullmatch(row.counter)]
        if invalid_counters:
            failures.append(f"Invalid counter format rows: {invalid_counters!r}")

        invalid_national_ids = [row.national_id for row in ledger_data if not NATIONAL_ID_PATTERN.fullmatch(row.national_id)]
        if invalid_national_ids:
            failures.append(f"Invalid national_id rows: {invalid_national_ids!r}")

        duplicates = [counter for counter, count in Counter(row.counter for row in ledger_data).items() if count > 1]
        if duplicates:
            failures.append(f"Duplicate counters detected: {duplicates!r}")

        sequence_bounds = conn.execute(
            select(counter_sequences.c.year_code, counter_sequences.c.prefix, counter_sequences.c.next_seq).where(
                (counter_sequences.c.next_seq < 1) | (counter_sequences.c.next_seq > 10000)
            )
        ).fetchall()
        if sequence_bounds:
            failures.append(f"Sequence bounds violated: {sequence_bounds!r}")

        derived_map = _collect_sequence_mismatches((row.counter, row.year_code) for row in ledger_data)
        if derived_map:
            seq_rows = conn.execute(select(counter_sequences.c.year_code, counter_sequences.c.prefix, counter_sequences.c.next_seq)).fetchall()
            mismatches = []
            for row in seq_rows:
                key = (row.year_code, row.prefix)
                max_seq = derived_map.get(key)
                if max_seq is None:
                    continue
                expected_next = max_seq + 1
                if row.next_seq != expected_next:
                    mismatches.append((row.year_code, row.prefix, row.next_seq, expected_next))
            if mismatches:
                failures.append(f"Sequence alignment mismatches: {mismatches!r}")

    if failures:
        for failure in failures:
            logging.error(failure)
        return 1
    logging.info("Post-migration checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
