.PHONY: counter-tests backfill-dry-run migrate post-checks bandit mypy serve-metrics ci-checks fault-tests spec-matrix static-checks

counter-tests:
	pytest tests/counter

backfill-dry-run:
	python scripts/backfill_counters.py data/backfill_sample.csv 54 --dry-run --report data/backfill_dry_run_sample.csv

migrate:
	python -m alembic upgrade head

post-checks:
	python scripts/post_migration_checks.py

bandit:
	bandit -q -r src/domain/counter src/infrastructure/counter src/api scripts assign_counter.py

mypy:
	mypy --strict --follow-imports=skip assign_counter.py scripts/backfill_counters.py scripts/post_migration_checks.py scripts/generate_spec_matrix.py scripts/serve_metrics.py src/api/counter_api.py src/domain/counter src/infrastructure/counter

serve-metrics:
	python scripts/serve_metrics.py

ci-checks:
	rm -f reports/ci_counter.sqlite
	mkdir -p reports
	DATABASE_URL=sqlite+pysqlite:///$(PWD)/reports/ci_counter.sqlite \
	PII_HASH_SALT=ci-salt \
	COUNTER_ENV=dev \
	COUNTER_METRICS_PORT=9102 \
	python -m alembic upgrade head
	DATABASE_URL=sqlite+pysqlite:///$(PWD)/reports/ci_counter.sqlite \
	PII_HASH_SALT=ci-salt \
	COUNTER_ENV=dev \
	COUNTER_METRICS_PORT=9102 \
	python scripts/post_migration_checks.py
	$(MAKE) spec-matrix
	git diff --exit-code reports/spec_matrix.md
	pytest tests/counter

fault-tests:
	pytest -q -o addopts="" tests/counter/test_fault_injection.py tests/counter/test_post_migration_checks.py

spec-matrix:
	python scripts/generate_spec_matrix.py

static-checks: bandit mypy
