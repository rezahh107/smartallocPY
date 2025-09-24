from __future__ import annotations

from pathlib import Path

import yaml

from scripts import generate_spec_matrix


def test_alert_rules_yaml_valid() -> None:
    alerts_dir = Path("docs/dashboard/alerts")
    for alert_file in alerts_dir.glob("*.yaml"):
        with alert_file.open("r", encoding="utf-8") as handle:
            assert yaml.safe_load(handle.read()) is not None


def test_spec_matrix_generation(tmp_path) -> None:
    output = tmp_path / "spec_matrix.md"
    generate_spec_matrix.write_matrix(output)
    content = output.read_text(encoding="utf-8")
    assert "| Requirement | Tests / Assets |" in content
