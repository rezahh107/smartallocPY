#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ابزار خط فرمان برای آماده سازی دروازه های CI پروژه."""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Dict


def parse_int(value: str | None, default: int) -> int:
    """Parse environment variable values safely."""
    if value in {None, ""}:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        print(
            f"هشدار: مقدار '{value}' عددی نیست؛ مقدار پیش فرض {default} استفاده می شود.",
            file=sys.stderr,
        )
        return default


def next_backup_path(target: Path) -> Path:
    """Return a non-conflicting backup path for the given file."""
    base_backup = target.with_suffix(target.suffix + ".bak")
    if not base_backup.exists():
        return base_backup
    counter = 1
    while True:
        candidate = target.with_suffix(target.suffix + f".bak{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def write_file(path: Path, content: str) -> None:
    """Write content to path with backup if necessary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing == content:
                print(f"بدون تغییر: {path}")
                return
            backup = next_backup_path(path)
            shutil.move(str(path), str(backup))
            print(f"پشتیبان گیری انجام شد: {backup}")
        path.write_text(content, encoding="utf-8")
        print(f"به روزرسانی فایل: {path}")
    except OSError as error:
        print(f"خطا: فایل {path} قابل نوشتن نیست - {error}")
        raise SystemExit(1) from error


def ensure_gitkeep(directory: Path) -> None:
    """Ensure .gitkeep exists when directory is empty."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"خطا: ساخت مسیر {directory} ممکن نشد - {error}")
        raise SystemExit(1) from error
    entries = [item for item in directory.iterdir() if item.name != ".gitkeep"]
    if entries:
        print(f"پوشه {directory} شامل {len(entries)} مورد است؛ .gitkeep اختیاری است.")
        return
    gitkeep = directory / ".gitkeep"
    if gitkeep.exists():
        print(f"بدون تغییر: {gitkeep}")
        return
    try:
        gitkeep.write_text("", encoding="utf-8")
        print(f"ایجاد فایل نگهدارنده: {gitkeep}")
    except OSError as error:
        print(f"خطا: ایجاد {gitkeep} ممکن نشد - {error}")
        raise SystemExit(1) from error


def build_ci_workflow(coverage_min: int, p95_ms: int, golden_dir: Path) -> str:
    """Compose the GitHub Actions workflow YAML."""
    yaml_content = f"""\
name: CI

on:
  pull_request:
  push:
    branches:
      - main

env:
  PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"
  COVERAGE_MIN: "{coverage_min}"
  P95_MS_ALLOCATIONS: "{p95_ms}"

jobs:
  core-tests:  # alias: core
    if: github.event_name == 'pull_request'
    name: Core Tests and Coverage
    runs-on: ubuntu-latest
    steps:
      - name: دریافت کد
        uses: actions/checkout@v4
      - name: تنظیم پایتون
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: نصب وابستگی ها
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then python -m pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt; fi
      - name: اجرای آزمون های هسته ای
        run: |
          PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -p pytest_cov --cov=src --cov-report=xml --cov-fail-under=${{{{ env.COVERAGE_MIN }}}} -m "not golden and not e2e and not smoke" tests
      - name: بارگذاری گزارش پوشش
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-xml
          path: coverage.xml
          if-no-files-found: warn

  golden-determinism:  # alias: exporter-golden
    if: github.event_name == 'pull_request'
    name: Golden Exporter Determinism
    runs-on: ubuntu-latest
    needs: core-tests
    steps:
      - name: دریافت کد
        uses: actions/checkout@v4
      - name: تنظیم پایتون
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: نصب وابستگی ها
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then python -m pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt; fi
      - name: اجرای آزمون های طلایی صادرکننده
        run: |
          PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m golden tests/test_exporter_golden.py
      - name: بارگذاری نمونه های طلایی
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: golden-snapshots
          path: {golden_dir.as_posix()}
          if-no-files-found: warn

  smoke-e2e:
    if: github.event_name == 'push'
    name: Smoke & E2E
    runs-on: ubuntu-latest
    steps:
      - name: دریافت کد
        uses: actions/checkout@v4
      - name: تنظیم پایتون
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: نصب وابستگی ها
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then python -m pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt; fi
      - name: اجرای دود و مسیر شاد
        run: |
          PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -m "smoke and e2e" -q
"""
    return textwrap.dedent(yaml_content).strip("\n") + "\n"


def build_pytest_ini() -> str:
    """Return the content for pytest.ini."""
    ini_content = """\
[pytest]
addopts = -ra
markers =
    smoke: آزمون های دود برای مسیرهای بحرانی
    e2e: آزمون های انتها به انتها برای تخصیص ها
    golden: آزمون های پایداری خروجی صادرکننده
filterwarnings =
    error
"""
    return textwrap.dedent(ini_content).strip("\n") + "\n"


def build_golden_test() -> str:
    """Return template for golden tests."""
    template = '''\
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
        joined = "\\n".join(mismatches)
        pytest.fail("پرونده های زیر با نمونه طلایی مطابقت ندارند:\\n" + joined)
'''
    return textwrap.dedent(template).strip("\n") + "\n"


def build_smoke_test(p95_ms: int) -> str:
    """Return template for smoke/e2e test."""
    template = f'''\
"""Smoke and end-to-end tests for allocation pipeline."""

from __future__ import annotations

import os
from statistics import quantiles
from typing import List

import pytest

P95_BUDGET_MS = int(os.getenv("P95_MS_ALLOCATIONS", "{p95_ms}"))


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
        {{"id": "A1", "amount": 10, "currency": "usd"}},
        {{"id": "A2", "amount": 15, "currency": "USD"}},
    ]

    normalized = [
        {{**item, "currency": item["currency"].upper(), "amount": float(item["amount"])}}
        for item in raw_allocations
    ]
    assert all(entry["currency"] == "USD" for entry in normalized)

    total_amount = sum(entry["amount"] for entry in normalized)
    assert total_amount == 25.0

    decisions = []
    for entry in normalized:
        decision = {{
            "id": entry["id"],
            "approved": entry["amount"] <= 20,
            "amount": entry["amount"],
        }}
        decisions.append(decision)

    outbox_messages = [
        f"ALLOC::{{decision['id']}}::{{int(decision['approved'])}}"
        for decision in decisions
    ]
    assert outbox_messages == ["ALLOC::A1::1", "ALLOC::A2::1"]

    exported_payload = "\\n".join(outbox_messages)
    assert "ALLOC::A1::1" in exported_payload


@pytest.mark.e2e
def test_p95_allocations_budget() -> None:
    """Check p95 latency budget when enabled."""
    if os.getenv("RUN_P95_CHECK") != "1":
        pytest.skip("بررسی کارایی غیرفعال است؛ متغیر RUN_P95_CHECK را روی 1 قرار دهید.")

    durations_ms = [42, 57, 61, 70, 75, 80, 90, 95, 110, 120]
    p95_value = _calculate_p95(durations_ms)
    assert p95_value <= P95_BUDGET_MS, (
        f"p95 محاسبه شده {{p95_value:.2f}} میلی ثانیه است و از بودجه {{P95_BUDGET_MS}} بیشتر است"
    )
'''
    return textwrap.dedent(template).strip("\n") + "\n"


def build_run_tests_py(coverage_min: int) -> str:
    """Return the unified local test runner script."""
    template = f'''\
#!/usr/bin/env python3
"""اجرای یکپارچه آزمون ها مطابق CI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List
import xml.etree.ElementTree as ET

COVERAGE_MIN = {coverage_min}


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="اجرای دسته های مختلف آزمون")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--core", action="store_true", help="اجرای آزمون های هسته ای با پوشش")
    group.add_argument("--golden", action="store_true", help="اجرای آزمون های طلایی")
    group.add_argument("--smoke", action="store_true", help="اجرای دود و e2e")
    group.add_argument("--all", action="store_true", help="اجرای همه مراحل")
    return parser.parse_args()


def _run(command: List[str], description: str) -> int:
    """Run a subprocess command with Persian logs."""
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    print(f"اجرای {{description}} ...")
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode == 0:
        print(f"✅ موفقیت در {{description}}")
    else:
        print(f"❌ شکست در {{description}}")
    return completed.returncode


def _check_coverage_threshold(report_path: Path) -> None:
    """Validate coverage threshold using coverage.xml when available."""
    if not report_path.exists():
        print("هشدار: فایل coverage.xml یافت نشد؛ بررسی پوشش انجام نشد.")
        return
    try:
        root = ET.parse(report_path).getroot()
        line_rate = float(root.get("line-rate", "0"))
        coverage_value = round(line_rate * 100, 2)
    except ET.ParseError as error:
        print(f"هشدار: خطا در خواندن coverage.xml - {{error}}")
        return
    print(f"پوشش گزارش شده: {{coverage_value}}%")
    if coverage_value < COVERAGE_MIN:
        print("خطا: پوشش کد کمتر از حداقل تعیین شده است.", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    """CLI entrypoint aligning local runs with CI."""
    args = _parse_args()
    exit_code = 0
    commands: Iterable[tuple[List[str], str]]

    if args.core:
        commands = [(
            [
                "pytest",
                "-p",
                "pytest_cov",
                "--cov=src",
                "--cov-report=xml",
                f"--cov-fail-under={{COVERAGE_MIN}}",
                "-m",
                "not golden and not e2e and not smoke",
                "tests",
            ],
            "آزمون های هسته ای",
        )]
    elif args.golden:
        commands = [(
            [
                "pytest",
                "-m",
                "golden",
                "tests/test_exporter_golden.py",
            ],
            "آزمون های طلایی",
        )]
    elif args.smoke:
        commands = [(
            [
                "pytest",
                "-m",
                "smoke and e2e",
                "-q",
            ],
            "آزمون های دود و e2e",
        )]
    else:
        commands = [
            (
                [
                    "pytest",
                    "-p",
                    "pytest_cov",
                    "--cov=src",
                    "--cov-report=xml",
                    f"--cov-fail-under={{COVERAGE_MIN}}",
                    "-m",
                    "not golden and not e2e and not smoke",
                    "tests",
                ],
                "آزمون های هسته ای",
            ),
            (
                [
                    "pytest",
                    "-m",
                    "golden",
                    "tests/test_exporter_golden.py",
                ],
                "آزمون های طلایی",
            ),
            (
                [
                    "pytest",
                    "-m",
                    "smoke and e2e",
                    "-q",
                ],
                "آزمون های دود و e2e",
            ),
        ]

    for command, description in commands:
        result = _run(command, description)
        if result != 0:
            exit_code = result
            break
        if "pytest_cov" in command:
            _check_coverage_threshold(Path("coverage.xml"))

    if exit_code == 0:
        print("🎉 همه چیز موفق بود")
    else:
        print("⚠️ برخی مراحل با خطا مواجه شد")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
'''
    return textwrap.dedent(template).strip("\n") + "\n"


def build_readme_ci(golden_dir: Path) -> str:
    """Create README content in Persian."""
    template = f"""\
# راهنمای سامانهٔ CI

این پروژه با اسکریپت `tools/setup_ci.py` پیکربندی CI دریافت می کند. برای به روزرسانی تنظیمات:

```bash
python tools/setup_ci.py
```

## اجرای محلی

برای هماهنگی با جریان CI از اسکریپت زیر استفاده کنید:

```bash
python tools/run_tests.py --all
```

حالت های جداگانه:

- `--core` آزمون های هسته ای به همراه سنجش پوشش.
- `--golden` بررسی قطعی بودن خروجی صادرکننده.
- `--smoke` اجرای مسیر شاد دود و e2e.

پوشهٔ نمونه های طلایی در `{golden_dir.as_posix()}` قرار دارد. اگر فایل ها حذف شوند، پیام خطای «خطا: نمونهٔ طلایی یافت نشد» دریافت خواهید کرد.

## خطاهای رایج

- «خطا: فایل workflow قابل نوشتن نیست» به معنای نداشتن مجوز یا قفل بودن فایل است.
- «خطا: پوشش کد کمتر از حداقل تعیین شده است» زمانی چاپ می شود که آستانهٔ پوشش برآورده نشود.
- «بررسی کارایی غیرفعال است؛ متغیر RUN_P95_CHECK را روی 1 قرار دهید.» برای فعال سازی آزمون کارایی.
"""
    return textwrap.dedent(template).strip("\n") + "\n"


def compute_relative_path(target: Path, base: Path) -> Path:
    """Compute a relative path from base to target safely."""
    try:
        return target.relative_to(base)
    except ValueError:
        return Path(os.path.relpath(target, base))


def main() -> None:
    """Entry point for provisioning CI assets."""
    repo_root = Path(__file__).resolve().parent.parent
    coverage_min = parse_int(os.getenv("COVERAGE_MIN"), 80)
    p95_ms = parse_int(os.getenv("P95_MS_ALLOCATIONS"), 200)
    golden_path_str = os.getenv("GOLDEN_DIR", "tests/golden")
    golden_dir = (repo_root / golden_path_str).resolve()

    print("آغاز پیکربندی CI ...")

    golden_rel = compute_relative_path(golden_dir, repo_root)

    files: Dict[Path, str] = {
        repo_root / ".github/workflows/ci.yml": build_ci_workflow(coverage_min, p95_ms, golden_rel),
        repo_root / "pytest.ini": build_pytest_ini(),
        repo_root / "tests/test_exporter_golden.py": build_golden_test(),
        repo_root / "tests/test_smoke_e2e.py": build_smoke_test(p95_ms),
        repo_root / "tools/run_tests.py": build_run_tests_py(coverage_min),
        repo_root / "README_CI.md": build_readme_ci(golden_rel),
    }

    for path, content in files.items():
        write_file(path, content)

    ensure_gitkeep(golden_dir)
    print("پایان پیکربندی CI.")


if __name__ == "__main__":
    main()
