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

COVERAGE_MIN = 80


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
    print(f"اجرای {description} ...")
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode == 0:
        print(f"✅ موفقیت در {description}")
    else:
        print(f"❌ شکست در {description}")
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
        print(f"هشدار: خطا در خواندن coverage.xml - {error}")
        return
    print(f"پوشش گزارش شده: {coverage_value}%")
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
                f"--cov-fail-under={COVERAGE_MIN}",
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
                    f"--cov-fail-under={COVERAGE_MIN}",
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
