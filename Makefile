.PHONY: test-gate test-artifacts security guard ci-local
	
test-gate:
	pytest -q -o addopts="" --cov=src.core.models.mentor --cov-report=term-missing --cov-fail-under=90

test-artifacts:
	mkdir -p reports
	pytest -q -o addopts="" --cov=src.core.models --cov-report=term-missing --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml

security:
	bandit -q -r src/core/models -x tests

guard:
	@git grep -n "mentor_phase1" -- src tests || true
	@test -z "$$(git grep -n "mentor_phase1" -- src tests)"

ci-local: guard test-gate test-artifacts security
