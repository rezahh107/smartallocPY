
| Requirement | Tests / Assets |
| --- | --- |
| SSOT gender→prefix mapping | `tests/counter/test_ports.py::test_prefix_map` |
| Counter regex invariant | `tests/counter/test_ports.py::test_counter_regex_matches_examples`, `tests/counter/test_property_based.py::test_counter_format_invariant` |
| Validation errors with Persian payloads and codes | `tests/counter/test_service_validation.py`, `tests/counter/test_api.py::test_assign_counter_error_payload` |
| Reuse before generate, idempotent ledger binding | `tests/counter/test_service_unit.py::test_get_or_create_idempotent`, `tests/counter/test_service_integration.py::test_generate_then_reuse` |
| Sequence reservation + conflicts + overflow | `tests/counter/test_service_integration.py::test_parallel_generation_unique`, `tests/counter/test_service_integration.py::test_bootstrap_sequence`, `tests/counter/test_service_integration.py::test_overflow_triggers_error` |
| API signature assign_counter(...) & concurrency guarantees | `tests/counter/test_api.py::test_parallel_calls_single_assignment`, `tests/counter/test_api.py::test_assign_counter_year_mismatch` |
| Backfill mismatch detection, dry-run, and sequence reconciliation | `tests/counter/test_backfill.py::test_backfill_reports_gender_mismatch`, `tests/counter/test_backfill.py::test_backfill_dry_run_no_changes`, `tests/counter/test_backfill.py::test_backfill_derives_sequence`, `tests/counter/test_backfill.py::test_backfill_idempotent_run` |
| Year boundary provider stability | `tests/counter/test_year_provider.py::test_year_provider_boundary_consistency`, `tests/counter/test_year_provider.py::test_year_provider_after_cutover` |
| Property-based safety of generated counters | `tests/counter/test_property_based.py::test_counter_format_invariant` |
| Post-migration validation tooling & CI gate | `scripts/post_migration_checks.py`, `tests/counter/test_post_migration_checks.py::test_post_checks_fail_on_bad_data` |
| Observability metrics, exporter health, and dashboards | `tests/counter/test_metrics.py`, `tests/counter/test_docs_assets.py::test_alert_rules_yaml_valid`, `docs/dashboard/counter_dashboard.json`, `docs/dashboard/alerts/counter_alerts.yaml` |
| Fault-injection remediation for duplicate national_id/counter | `tests/counter/test_fault_injection.py` |
| Sample operator artifacts (dry-run CSV) | `data/backfill_dry_run_sample.csv` |
| Spec matrix regeneration automation | `scripts/generate_spec_matrix.py`, `tests/counter/test_docs_assets.py::test_spec_matrix_generation`, `make spec-matrix` |
