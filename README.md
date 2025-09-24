# Student Allocation System

![CI](https://github.com/smartallocPY/smartallocPY/actions/workflows/ci.yml/badge.svg?branch=main)

A modular Python project for managing student-to-mentor allocations. The project is structured around clear layers for models, services, utilities, API endpoints, and configuration files.

## Project Structure

```
student-allocation-system/
├── src/
│   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── api/
│   │   └── endpoints/
│   └── config/
├── tests/
│   ├── unit/
│   └── integration/
├── data/
│   ├── sample/
│   └── config/
```

## Getting Started

1. Create and populate an `.env` file based on `.env.example`.
2. Install dependencies using `pip install -r requirements.txt`.
3. Run unit tests with `pytest`.
4. Start the API by running `uvicorn src.api.main:app --reload`.

## Features

- Pydantic models for students, mentors, assignments, managers, and schools.
- Utility helpers for normalising phone numbers and Persian text.
- Allocation service for pairing students with mentors.
- REST API built with FastAPI exposing allocation and health endpoints.
- Configuration management via environment variables using Pydantic settings.
- Deterministic counter service with Postgres-backed ledger, Prometheus metrics, and structured logging.

## Counter Service (Phase 2)

Run migrations with Alembic once the database URL and `PII_HASH_SALT` are exported:

```bash
alembic upgrade head
```

Assign or reuse counters from the CLI (year code is injected explicitly and validated by the API facade):

```bash
export DATABASE_URL=postgresql+psycopg://user:pass@localhost/db
export PII_HASH_SALT="super-secret"
export COUNTER_METRICS_PORT=9102
export COUNTER_ENV=prod
python assign_counter.py 1234567890 0 54
```

<!-- README excerpt: CounterService usage -->
```python
from sqlalchemy import create_engine

from src.domain.counter.service import CounterService
from src.infrastructure.counter.metrics import PrometheusCounterMetrics
from src.infrastructure.counter.postgres_repo import PostgresCounterRepository
from src.infrastructure.counter.year_provider import FixedAcademicYearProvider

engine = create_engine("postgresql+psycopg://user:pass@localhost/db", future=True)
service = CounterService(
    repository=PostgresCounterRepository(engine),
    year_provider=FixedAcademicYearProvider("54"),
    metrics=PrometheusCounterMetrics(),
    pii_hash_salt="super-secret",
)
counter = service.get_or_create("1234567890", 1)
print(counter)
```

The service exports Prometheus counters (`counter_reuse_total`, `counter_generated_total`, `counter_conflict_total`, `counter_overflow_total`, `counter_backfill_mismatch_total`) and the gauge `counter_last_sequence_position`. Sample Grafana panels and alert rules live under `docs/dashboard/`.

### Counter service operations playbook

- Metrics exporter: every CLI/daemon invocation automatically boots a Prometheus HTTP server on `COUNTER_METRICS_PORT` and flips the health gauge `counter_metrics_http_started` to `1`. Scrape `http://127.0.0.1:${COUNTER_METRICS_PORT}/metrics` to confirm counters such as `counter_generated_total` advance during assignments. Use `make serve-metrics` to run a long-lived exporter for dashboards during local testing.
- Fault drills: `make fault-tests` exercises duplicate-counter/national-id remediation paths and asserts conflict logs/metrics are emitted.
- Schema safety: `make ci-checks` provisions a disposable SQLite database, applies Alembic migrations, runs `scripts/post_migration_checks.py`, regenerates the spec matrix, and executes the counter test-suite with a hard coverage gate of 95%.
- Backfill tooling: `make backfill-dry-run` keeps the ledger untouched while writing mismatch CSVs. Re-run with `--dry-run` omitted to apply reconciled sequences idempotently.
- Spec compliance tracking: regenerate the requirement-to-test matrix with `make spec-matrix`, which updates `reports/spec_matrix.md` directly from the authoritative mapping.
- Static analysis: `make static-checks` enforces the Bandit security scan and strict mypy type-checks on the counter stack.

Alerting assets are published under `docs/dashboard/alerts/` (validated YAML) and include rules for overflow, conflict spikes, and exporter downtime.

<!-- README excerpt: assign_counter operator workflow -->
```bash
make counter-tests
make migrate
python scripts/backfill_counters.py data/backfill_sample.csv 54 --dry-run --report reports/backfill_report.csv
python scripts/post_migration_checks.py
python assign_counter.py 1234567890 0 54
```

## Migration

The legacy phase-one mentor module has been fully replaced by the canonical `src.core.models.mentor` module. Import mentor types via `from src.core.models.mentor import Mentor, MentorType, AvailabilityStatus` going forward.

```python
from src.core.models.mentor import Mentor, MentorType

mentor = Mentor(
    mentor_id=101,
    first_name="Example",
    last_name="Mentor",
    gender=1,
    mentor_type=MentorType.NORMAL,
    manager_id=42,
    special_schools={10, 20},
    allowed_groups={7, 8},
)

mentor_dict = mentor.to_dict()
# mentor_dict["special_schools"] == [10, 20]
# mentor_dict["allowed_groups"] == [7, 8]
```

## Development

- `tests/unit` contains isolated unit tests.
- `tests/integration` contains flow-based integration tests.
- Sample data and configuration files are stored in `data/`.
- Track spec mismatches via `docs/TODOs_phase2.md`; refresh the list with `git grep -n "TODO(spec-mismatch)"`.

### Testing & Coverage
- Run tests: `pytest -q`
- Enforced coverage: ≥90% on `src/core/models/mentor.py`
- CI uploads `reports/coverage.xml` and `reports/junit.xml` as artifacts.

### Local CI Parity
- Gate mentor coverage (≥90%): `make test-gate`
- Full-package reports (artifacts): `make test-artifacts`
- Security scan: `make security`
- Legacy import guard: `make guard`
- Run all (CI-like): `make ci-local`

Artifacts are written to `reports/coverage.xml` and `reports/junit.xml`.

## License

This project is provided as-is for educational purposes.
